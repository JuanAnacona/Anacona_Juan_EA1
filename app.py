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
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            documento TEXT NOT NULL,
            placa TEXT NOT NULL,
            celda_asignada TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS celdas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL,
            estado TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL,
            monto REAL NOT NULL,
            metodo_pago TEXT NOT NULL,
            fecha_pago TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

@app.route('/api/usuarios', methods=['POST'])
def registrar_usuario():
    data = request.json
    nombre = data.get('nombre')
    documento = data.get('documento')
    placa = data.get('placa').upper()
    celda = data.get('celda_asignada')
    
    conn = sqlite3.connect('autos_colombia.db')
    c = conn.cursor()
    c.execute("INSERT INTO usuarios (nombre, documento, placa, celda_asignada) VALUES (?, ?, ?, ?)",
              (nombre, documento, placa, celda))
    # Actualizar estado de la celda a Reservada
    c.execute("UPDATE celdas SET estado = 'RESERVADA' WHERE numero = ?", (celda,))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Usuario registrado y celda asignada correctamente"}), 201

# CASO DE USO: Consultar Mapa de Celdas
@app.route('/api/celdas', methods=['GET'])
def obtener_celdas():
    conn = sqlite3.connect('autos_colombia.db')
    c = conn.cursor()
    c.execute("SELECT numero, estado FROM celdas")
    celdas = [{"numero": r[0], "estado": r[1]} for r in c.fetchall()]
    conn.close()
    return jsonify(celdas), 200

@app.route('/api/pagos', methods=['POST'])
def registrar_pago():
    data = request.get_json()
    placa = data.get('placa')
    monto = data.get('monto')
    metodo_pago = data.get('metodo_pago') # Efectivo, Tarjeta, Transferencia

    if not placa or not monto or not metodo_pago:
        return jsonify({'error': 'Faltan datos para procesar el pago'}), 400

    conn = sqlite3.connect('autos_colombia.db')
    c = conn.cursor()

    try:
        # 1. Registrar el pago en la base de datos
        c.execute("INSERT INTO pagos (placa, monto, metodo_pago) VALUES (?, ?, ?)", 
                  (placa, monto, metodo_pago))
        
        # 2. Liberar la celda si el cliente era de mensualidad (opcional según tu lógica)
        # o actualizar el estado del vehículo a "Pagado/Inactivo"
        c.execute("UPDATE celdas SET estado = 'LIBRE' WHERE numero = (SELECT celda_asignada FROM usuarios WHERE placa = ?)", (placa,))
        
        conn.commit()
        return jsonify({
            'mensaje': 'Pago registrado exitosamente',
            'recibo': {
                'placa': placa,
                'total_pagado': monto,
                'metodo': metodo_pago,
                'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)