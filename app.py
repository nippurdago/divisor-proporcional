import decimal
from flask import Flask, render_template, request

# --- Configuración Decimal Precisa ---
# Usar Decimal es crucial para evitar errores de redondeo con floats,
# especialmente cuando la suma final debe ser exacta.
# Establece una precisión suficiente para los cálculos intermedios.
decimal.getcontext().prec = 30
ONE_DP = decimal.Decimal('0.1') # Para redondear a 1 decimal

app = Flask(__name__)

def distribute_proportionally(total_value_str, proportions_str_list):
    """
    Divide un valor total según una lista de proporciones, redondea a 1 decimal
    y ajusta para que la suma sea exacta.

    Args:
        total_value_str (str): El valor total como cadena.
        proportions_str_list (list): Lista de proporciones como cadenas.

    Returns:
        tuple: (list or None, str or None)
               - Lista de valores ajustados formateados a 1 decimal (como str).
               - Mensaje de error si ocurre alguno, None si no hay error.
    """
    try:
        total_value = decimal.Decimal(total_value_str)
        proportions = [decimal.Decimal(p) for p in proportions_str_list]

        # --- Validaciones ---
        if total_value < 0:
            return None, "El valor total no puede ser negativo."
        if not proportions:
            return None, "La lista de proporciones no puede estar vacía."
        if any(p < 0 for p in proportions):
            return None, "Las proporciones no pueden ser negativas."

        sum_proportions = sum(proportions)

        if sum_proportions == 0:
            # Si el total también es 0, podemos devolver ceros.
            if total_value == 0:
                 return ['0.0'] * len(proportions), None
            # Si el total no es 0 pero las proporciones suman 0, es un error.
            return None, "La suma de las proporciones es cero, no se puede dividir un total distinto de cero."

        # --- Cálculo Inicial y Redondeo ---
        initial_shares = []
        rounded_shares = []
        remainders = [] # Guardará la diferencia entre el valor real y el redondeado

        for i, p in enumerate(proportions):
            # Calcula la parte proporcional exacta
            exact_share = (p / sum_proportions) * total_value
            initial_shares.append(exact_share)

            # Redondea a 1 decimal (ROUND_HALF_UP es el redondeo estándar)
            rounded_share = exact_share.quantize(ONE_DP, rounding=decimal.ROUND_HALF_UP)
            rounded_shares.append(rounded_share)

            # Guarda el residuo y el índice original
            remainders.append({'remainder': exact_share - rounded_share, 'index': i})

        # --- Ajuste por Diferencia de Redondeo ---
        current_sum = sum(rounded_shares)
        difference = total_value - current_sum

        # Si hay diferencia, la distribuimos
        if difference != decimal.Decimal('0.0'):
            # Ordena por residuo: los mayores primero si falta, los menores (más negativos) primero si sobra
            remainders.sort(key=lambda x: x['remainder'], reverse=(difference > 0))

            # Cantidad a ajustar por paso (siempre 0.1 o -0.1)
            step = ONE_DP if difference > 0 else -ONE_DP
            num_steps = int(abs(difference / step)) # Cuántos ajustes de 0.1 necesitamos

            # Comprobación por si acaso (muy improbable con Decimal)
            if num_steps > len(rounded_shares):
                 print(f"Advertencia: Se necesitan {num_steps} ajustes pero solo hay {len(rounded_shares)} elementos.")
                 num_steps = len(rounded_shares) # Ajusta lo posible

            # Aplica el ajuste a los elementos con mayor/menor residuo
            for i in range(num_steps):
                index_to_adjust = remainders[i]['index']
                rounded_shares[index_to_adjust] += step
                # Re-redondear por si acaso (aunque sumar/restar 0.1 no debería cambiarlo)
                rounded_shares[index_to_adjust] = rounded_shares[index_to_adjust].quantize(ONE_DP, rounding=decimal.ROUND_HALF_UP)


        # --- Formateo Final ---
        # Devuelve los resultados como cadenas formateadas a 1 decimal
        final_results = [f"{val:.1f}" for val in rounded_shares]

        # Verificación final (opcional pero recomendable)
        final_sum_check = sum(decimal.Decimal(res) for res in final_results)
        if final_sum_check != total_value.quantize(ONE_DP, rounding=decimal.ROUND_HALF_UP):
             # Esto podría ocurrir si el total original tiene más decimales y el redondeo final no coincide
             print(f"Advertencia: La suma final ({final_sum_check}) no coincide exactamente con el total redondeado ({total_value.quantize(ONE_DP, rounding=decimal.ROUND_HALF_UP)}). Total original: {total_value}")
             # Podrías devolver un error aquí si es crítico
             # return None, f"Error de precisión: la suma final {final_sum_check} no coincide con el total esperado."


        return final_results, None

    except decimal.InvalidOperation:
        return None, "Error: Asegúrate de que el total y todas las proporciones sean números válidos."
    except Exception as e:
        # Captura cualquier otro error inesperado
        print(f"Error inesperado: {e}") # Log para depuración
        return None, f"Ocurrió un error inesperado durante el cálculo: {e}"


@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    error_message = None
    input_total = ''
    input_proportions = ''

    if request.method == 'POST':
        input_total = request.form.get('total_value', '').strip()
        input_proportions_raw = request.form.get('proportions', '').strip()

        # Procesar la entrada de proporciones (permite comas, espacios, saltos de línea)
        # Divide por espacios, comas o saltos de línea y filtra elementos vacíos
        proportions_list = [
            p.strip() for p in input_proportions_raw.replace(',', ' ').replace('\n', ' ').split() if p.strip()
        ]

        if not input_total:
             error_message = "Por favor, ingresa el valor total."
        elif not proportions_list:
             error_message = "Por favor, ingresa al menos un número de proporción."
             input_proportions = input_proportions_raw # Mantener la entrada original en el textarea
        else:
            # Llamar a la función de cálculo
            results, error_message = distribute_proportionally(input_total, proportions_list)
            input_proportions = input_proportions_raw # Mantener la entrada original en el textarea

    return render_template('index.html',
                           results=results,
                           error=error_message,
                           input_total=input_total,
                           input_proportions=input_proportions)

