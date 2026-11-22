from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)


def init_db():
    conn = sqlite3.connect('autos_colombia.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS registro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL,
            tipo_vehiculo TEXT NOT NULL,
            fecha_entrada TEXT NOT NULL,
            fecha_salida TEXT,
            estado TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

# CASO DE USO: Registrar Entrada de Vehículo
@app.route('/api/entrada', methods=['POST'])
def registrar_entrada():
    data = request.json
    placa = data.get('placa').upper()
    tipo = data.get('tipo_vehiculo')
    fecha_entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect('autos_colombia.db')
    c = conn.cursor()
    c.execute("INSERT INTO registro (placa, tipo_vehiculo, fecha_entrada, estado) VALUES (?, ?, ?, 'ACTIVO')",
              (placa, tipo, fecha_entrada))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": f"Entrada exitosa: Vehículo {placa}", "fecha": fecha_entrada}), 201

# CASO DE USO: Registrar Salida de Vehículo
@app.route('/api/salida', methods=['POST'])
def registrar_salida():
    data = request.json
    placa = data.get('placa').upper()
    fecha_salida = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect('autos_colombia.db')
    c = conn.cursor()
    
    # Buscar si el vehículo está en el parqueadero actualmente
    c.execute("SELECT id FROM registro WHERE placa = ? AND estado = 'ACTIVO'", (placa,))
    row = c.fetchone()
    
    if row:
        # Actualizar la fecha de salida y cambiar el estado
        c.execute("UPDATE registro SET fecha_salida = ?, estado = 'FINALIZADO' WHERE id = ?", (fecha_salida, row[0]))
        conn.commit()
        conn.close()
        return jsonify({"mensaje": f"Salida exitosa: Vehículo {placa}", "fecha": fecha_salida}), 200
    else:
        conn.close()
        return jsonify({"error": "Vehículo no encontrado o ya registró salida."}), 404

# Servicio adicional para ver los vehículos parqueados (Mockup)
@app.route('/api/vehiculos', methods=['GET'])
def obtener_vehiculos():
    conn = sqlite3.connect('autos_colombia.db')
    c = conn.cursor()
    c.execute("SELECT id, placa, tipo_vehiculo, fecha_entrada FROM registro WHERE estado = 'ACTIVO'")
    registros = [{"id": r[0], "placa": r[1], "tipo": r[2], "entrada": r[3]} for r in c.fetchall()]
    conn.close()
    return jsonify(registros), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True)