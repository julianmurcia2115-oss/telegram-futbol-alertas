def ejecutar_ciclo():
    """Una pasada completa: recibir Telegram + actualizar resultados."""
    recibir_telegram()
    print("⚽ ACTUALIZANDO RESULTADOS...")
    actualizar_resultados()

    apuestas = cargar_apuestas()
    stats = calcular_estadisticas(apuestas)
    print("====================================")
    print(f"📊 Total: {stats['total']} | 🟢 {stats['ganadas']} | 🔴 {stats['perdidas']} | 🟡 {stats['pendientes']}")
    print(f"💵 ${stats['ganancia']:,.0f} COP | 📈 {stats['efectividad']:.1f}% | ROI {stats['roi']:.2f}%")
    print("====================================")


def main():
    en_github_actions = os.getenv("GITHUB_ACTIONS") == "true"

    if en_github_actions:
        print("🚀 EJECUCIÓN ÚNICA (GitHub Actions)")
        ejecutar_ciclo()
        print("✅ EJECUCIÓN TERMINADA")
    else:
        print("🚀 BOT INICIADO (loop continuo — VPS)")
        estado = cargar_estado()
        ultima_verificacion = estado.get("ultima_verificacion_resultados", 0)

        while True:
            recibir_telegram()
            ahora_ts = time.time()
            if ahora_ts - ultima_verificacion >= RESULTADOS_INTERVALO:
                print("⚽ ACTUALIZANDO RESULTADOS...")
                actualizar_resultados()
                ultima_verificacion = ahora_ts
                estado = cargar_estado()
                estado["ultima_verificacion_resultados"] = ultima_verificacion
                guardar_estado(estado)

                apuestas = cargar_apuestas()
                stats = calcular_estadisticas(apuestas)
                print("====================================")
                print(f"📊 Total: {stats['total']} | 🟢 {stats['ganadas']} | 🔴 {stats['perdidas']} | 🟡 {stats['pendientes']}")
                print(f"💵 ${stats['ganancia']:,.0f} COP | 📈 {stats['efectividad']:.1f}% | ROI {stats['roi']:.2f}%")
                print("====================================")


if __name__ == "__main__":
    main()
