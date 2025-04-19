from flask import Flask, render_template, request, jsonify
import math
from datetime import datetime, timedelta

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
    tarifas_path = '/Users/dds/Documents/Dany25/Herramientas/electrical_sizing/tarifas.json'
    
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
        # Obtener datos del formulario
        autonomia_km = float(request.form['autonomia_km'])
        capacidad_bateria_kwh = float(request.form['capacidad_bateria_kwh'])
        potencia_cargador_kw = float(request.form['potencia_cargador_kw'])
        distancia_recorrida_km = float(request.form['distancia_recorrida_km'])

        # Calcular el consumo de energía (kWh por km)
        consumo_por_km = capacidad_bateria_kwh / autonomia_km

        # Calcular la energía necesaria para recargar la distancia recorrida
        energia_necesaria_kwh = consumo_por_km * distancia_recorrida_km

        # Calcular el tiempo de carga en horas
        tiempo_carga_horas = energia_necesaria_kwh / potencia_cargador_kw

        # Convertir el tiempo de carga a minutos
        tiempo_carga_minutos = tiempo_carga_horas * 60

        # Calcular minutos por kilómetro
        minutos_por_km = tiempo_carga_minutos / distancia_recorrida_km

        # Calcular kilómetros por minuto
        kilometros_por_minuto = distancia_recorrida_km / tiempo_carga_minutos if tiempo_carga_minutos > 0 else 0

        # Factor conservador
        factor_conservador = 2  # 1 km / 2 min
        tiempo_conservador_minutos = distancia_recorrida_km * factor_conservador

        # Calcular la energía diaria de transporte
        energia_diaria_transporte = distancia_recorrida_km * consumo_por_km

        return render_template(
            'resultado_carga.html',
            energia_necesaria_kwh=f"{energia_necesaria_kwh:.2f}",
            tiempo_carga_horas=f"{tiempo_carga_horas:.2f}",
            tiempo_carga_minutos=f"{tiempo_carga_minutos:.1f}",
            minutos_por_km=f"{minutos_por_km:.2f}",
            kilometros_por_minuto=f"{kilometros_por_minuto:.2f}",
            tiempo_conservador_minutos=f"{tiempo_conservador_minutos:.1f}",
            energia_diaria_transporte=f"{energia_diaria_transporte:.2f}",
            formula_energia_diaria=f"Energía = {distancia_recorrida_km} km/día × {consumo_por_km:.2f} kWh/km"
        )
    return render_template('calcular_carga.html')
    
if __name__ == '__main__':
    app.run(debug=True)