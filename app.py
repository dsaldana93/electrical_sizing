from flask import Flask, render_template, request, jsonify, redirect
import math
from datetime import datetime, timedelta
from decimal import Decimal, getcontext

# Configurar la precisión global para los cálculos con Decimal
getcontext().prec = 28  # Aumentar la precisión global para evitar errores

app = Flask(__name__)

# Tariff calculation functions
def calcular_tarifa_dac(kwh):
    if kwh <= 150:
        return 0.793 * kwh
    elif kwh <= 300:
        return 0.956 * kwh
    else:
        return 2.802 * kwh

# Electrical calculations
def calcular_paneles(watts_necesarios, potencia_panel):
    return math.ceil(watts_necesarios / potencia_panel)

def calcular_calibre(amperaje):
    if amperaje <= 15:
        return '14 AWG'
    elif amperaje <= 20:
        return '12 AWG'
    elif amperaje <= 30:
        return '10 AWG'
    else:
        return '8 AWG'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tarifa-dac', methods=['GET', 'POST'])
def tarifa_dac():
    if request.method == 'POST':
        kwh = float(request.form['kwh'])
        cost = calcular_tarifa_dac(kwh)
        
        # Determinar nivel de consumo
        if kwh <= 150:
            tier = "Básico (0-150 kWh)"
            rate = 0.793
        elif kwh <= 300:
            tier = "Intermedio (151-300 kWh)"
            rate = 0.956
        else:
            tier = "Alto Consumo (>300 kWh)"
            rate = 2.802
            
        return render_template('tarifa_dac.html',
                            costo=f"{cost:,.2f} MXN",
                            kwh=kwh,
                            nivel=tier,
                            tarifa=rate,
                            nombre_tarifa="Doméstica de Alto Consumo (DAC)")
    return render_template('tarifa_dac.html')

@app.route('/tarifa-1', methods=['GET', 'POST'])
def tarifa_1():
    if request.method == 'POST':
        # Lógica de cálculo para Tarifa 1
        return redirect(request.url)
    return render_template('tarifa_1.html')

@app.route('/tarifa-1f')
def tarifa_1f():
    return render_template('tarifa_1f.html')

@app.route('/tarifa-om')
def tarifa_om():
    return render_template('tarifa_om.html')

@app.route('/solar', methods=['GET', 'POST'])
def solar_calculation():
    if request.method == 'POST':
        # Input processing
        km_diarios = float(request.form['km'])
        capacidad_bateria = float(request.form['bateria'])
        eficiencia = 0.85  # Assume 85% efficiency
        
        # Energy calculations
        energia_necesaria = capacidad_bateria / eficiencia
        horas_sol = 5  # Average daily sun hours
        paneles_necesarios = math.ceil(energia_necesaria / horas_sol)
        
        # Electrical calculations
        voltaje = 120
        amperaje = (energia_necesaria * 1000) / voltaje
        calibre = calcular_calibre(amperaje)
        interruptor = f"{math.ceil(amperaje * 1.25)}A"
        
        # ROI Calculation
        costo_instalacion = paneles_necesarios * 15000  # $15,000 MXN per panel
        ahorro_mensual = 1500  # Example value
        meses_roi = costo_instalacion / ahorro_mensual
        
        # Prepare chart data with realistic timeline
        meses_roi_num = float(meses_roi)
        start_date = datetime.now()
        
        # Generate monthly data points until ROI is achieved
        chart_labels = []
        roi_data = []
        for month in range(0, int(meses_roi_num) + 1):
            chart_labels.append(f'Mes {month + 1}')
            roi_data.append((month / meses_roi_num) * 100)
        
        return render_template('resultado_solar.html',
                           paneles=paneles_necesarios,
                           calibre=calibre,
                           interruptor=interruptor,
                           costo_instalacion=f"{costo_instalacion:,.2f}",
                           meses_roi=f"{meses_roi:.1f}",
                           chart_labels=chart_labels,
                           roi_data=roi_data)
    return render_template('solar.html')

@app.route('/editar-tarifas', methods=['GET', 'POST'])
def editar_tarifas():
    import json
    tarifas_path = 'tarifas.json'
    
    if request.method == 'POST':
        nuevas_tarifas = request.form.to_dict()
        with open(tarifas_path, 'r') as file:
            tarifas = json.load(file)
        
        for tarifa, valores in tarifas.items():
            for key in valores.keys():
                tarifas[tarifa][key] = float(nuevas_tarifas.get(f"{tarifa}_{key}", tarifas[tarifa][key]))
        
        with open(tarifas_path, 'w') as file:
            json.dump(tarifas, file, indent=4)
        
        return jsonify({"message": "Tarifas actualizadas correctamente"}), 200
    
    with open(tarifas_path, 'r') as file:
        tarifas = json.load(file)
    
    return render_template('editar_tarifas.html', tarifas=tarifas)

@app.route('/calcular-carga', methods=['GET', 'POST'])
def calcular_carga():
    if request.method == 'POST':
        try:
            # Convertir los valores del formulario a Decimal
            autonomia_km = Decimal(request.form.get('autonomia_km', '0'))
            capacidad_bateria_kwh = Decimal(request.form.get('capacidad_bateria_kwh', '0'))
            potencia_cargador_kw = Decimal(request.form.get('potencia_cargador_kw', '0'))
            distancia_recorrida_km = Decimal(request.form.get('distancia_recorrida_km', '0'))
            frecuencia_carga = Decimal(request.form.get('frecuencia_carga', '0'))

            # Validar que los valores sean mayores a 0
            if autonomia_km <= 0 or capacidad_bateria_kwh <= 0 or potencia_cargador_kw <= 0 or distancia_recorrida_km <= 0 or frecuencia_carga <= 0:
                return jsonify({"error": "Todos los valores deben ser mayores a 0"}), 400

            # Calcular el rendimiento del vehículo eléctrico (kWh/km)
            rendimiento_vehiculo = capacidad_bateria_kwh / autonomia_km
            rendimiento_vehiculo = rendimiento_vehiculo.quantize(Decimal('0.01'))  # Redondear a 2 decimales

            # Validar que el rendimiento sea válido
            if rendimiento_vehiculo <= 0:
                return jsonify({"error": "El rendimiento del vehículo no puede ser menor o igual a 0"}), 400

            # Calcular el Consumo del vehiculo paso a paso
            # Paso 1: Calcular la distancia total recorrida
            distancia_total = frecuencia_carga * distancia_recorrida_km
            distancia_total = distancia_total.quantize(Decimal('0.01'))  # Redondear a 2 decimales

            # Paso 2: Calcular el consumo total del vehículo
            consumo_vehiculo = rendimiento_vehiculo * distancia_total
            consumo_vehiculo = consumo_vehiculo.quantize(Decimal('0.01'))  # Redondear a 2 decimales

            # Construir la fórmula con los valores sustituidos
            formula_consumo_vehiculo = (
                f"Consumo = {rendimiento_vehiculo:.2f} kWh/km × ({frecuencia_carga:.2f} días × {distancia_recorrida_km:.2f} km) = {consumo_vehiculo} kWh"
            )

            # Calcular la energía necesaria para recargar la distancia recorrida
            energia_necesaria_kwh = rendimiento_vehiculo * distancia_recorrida_km
            energia_necesaria_kwh = energia_necesaria_kwh.quantize(Decimal('0.00001'))  # Redondear a 5 decimales

            # Validar que la potencia del cargador no sea cero
            if potencia_cargador_kw <= 0:
                return jsonify({"error": "La potencia del cargador debe ser mayor a 0"}), 400

            # Calcular el tiempo de carga en horas
            tiempo_carga_horas = energia_necesaria_kwh / potencia_cargador_kw
            tiempo_carga_horas = tiempo_carga_horas.quantize(Decimal('0.01'))  # Redondear a 2 decimales
            tiempo_carga_minutos = tiempo_carga_horas * Decimal('60')
            tiempo_carga_minutos = tiempo_carga_minutos.quantize(Decimal('0.01'))  # Redondear a 2 decimales

            # Calcular minutos por kilómetro
            minutos_por_km = tiempo_carga_minutos / distancia_recorrida_km if distancia_recorrida_km > 0 else Decimal('0')
            minutos_por_km = minutos_por_km.quantize(Decimal('0.00001'))  # Redondear a 5 decimales

            # Calcular kilómetros por minuto
            kilometros_por_minuto = distancia_recorrida_km / tiempo_carga_minutos if tiempo_carga_minutos > 0 else Decimal('0')
            kilometros_por_minuto = kilometros_por_minuto.quantize(Decimal('0.00001'))  # Redondear a 5 decimales

            # Calcular el tiempo conservador en minutos
            factor_conservador = Decimal('2')  # 1 km / 2 min
            tiempo_conservador_minutos = distancia_recorrida_km * factor_conservador
            tiempo_conservador_minutos = tiempo_conservador_minutos.quantize(Decimal('0.01'))  # Redondear a 2 decimales

            # Calcular la energía diaria de transporte
            energia_diaria_transporte = distancia_recorrida_km * rendimiento_vehiculo
            energia_diaria_transporte = energia_diaria_transporte.quantize(Decimal('0.00001'))  # Redondear a 5 decimales

            # Devolver los resultados como JSON
            return jsonify({
                "rendimiento_vehiculo": f"{rendimiento_vehiculo:.2f} kWh/km",
                "consumo_vehiculo": f"{consumo_vehiculo} kWh",
                "formula_consumo_vehiculo": formula_consumo_vehiculo,
                "energia_necesaria_kwh": f"{energia_necesaria_kwh:.2f} kWh",
                "tiempo_carga_horas": f"{tiempo_carga_horas:.2f} horas",
                "tiempo_carga_minutos": f"{tiempo_carga_minutos:.2f} minutos",
                "minutos_por_km": f"{minutos_por_km:.5f}",
                "kilometros_por_minuto": f"{kilometros_por_minuto:.2f}",
                "tiempo_conservador_minutos": f"{tiempo_conservador_minutos:.2f}",
                "energia_diaria_transporte": f"{energia_diaria_transporte:.2f} kWh",
                "frecuencia_carga": f"{frecuencia_carga} días"  # Agregar frecuencia_carga
            })
        except ValueError:
            return jsonify({"error": "Por favor, ingrese valores numéricos válidos"}), 400

    return render_template('calcular_carga.html')
    
if __name__ == '__main__':
    app.run(debug=True)