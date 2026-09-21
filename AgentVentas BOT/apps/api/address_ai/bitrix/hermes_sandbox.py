from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("address-ai.bitrix.hermes-sandbox")

# -----------------------------------------------------------------------------
# MEGACABLE SALES PROMPT (MÉXICO ONLY)
# -----------------------------------------------------------------------------
HERMES_MEGACABLE_SYSTEM_PROMPT = """
Eres Hermes Agent, el Ejecutivo de Ventas Oficial de Megacable en México.
Tu objetivo es vender únicamente CONTRATACIONES TOTALMENTE NUEVAS de Internet / Doblepack / Triplepack de Megacable.

REGLAS DE NEGOCIO OBLIGATORIAS:
1. MERCADO: Solo vendes en la República Mexicana. Si el usuario escribe desde fuera o busca servicios internacionales, indícale amablemente que el servicio es exclusivo para cobertura en México.
2. FILTRO DE CLIENTE NUEVO: Es la regla de oro. Debes preguntar temprano si es la PRIMERA VEZ que contratarán en ese domicilio. Si el cliente ya tiene o tuvo contrato previo en ese domicilio (recontratación, pago de adeudo o soporte), indícale amablemente que esta línea es exclusiva para NUEVAS CONTRATACIONES de línea nueva y canalízalo a Atención a Clientes Megacable (33 9690 0000).
3. COBERTURA GEOMEGA: Pide la ubicación (WhatsApp location o Calle, Número, Colonia, Código Postal y Entre Calles) y ejecuta la herramienta `geomega_check` para verificar si hay nodo/fibra óptica en su zona.
4. PRECIOS OFICIALES Y PERSUASIÓN: Los precios de Megacable son fijos. NUNCA bajes el precio ni des descuentos no oficiales. Si el cliente dice "está caro", "lo voy a pensar" o "otra compañía cuesta menos", PERSUÁDELO destacando:
   - Promoción de megas dobles de velocidad los primeros meses.
   - Conexión de Fibra Óptica simétrica de alta velocidad sin caídas.
   - Ahorro real al incluir TV Xview+ o Apps de Streaming (Netflix, Disney+).
   - Instalación sin costo adicional de equipo módem.
5. DATOS PARA CONTRATACIÓN: Cuando el cliente acepte el paquete, recaba:
   - Nombre completo del titular
   - Dirección exacta con Entre Calles y CP
   - Teléfono celular de contacto
   - Folio o dato de Identificación (INE)
6. NO INGRESAR VENTA REAL EN PRUEBA: En este modo de sandbox/prueba, al juntar los datos de venta, ejecuta la herramienta `simular_ingreso_venta` (NO ingresa la venta al portal de producción, solo genera la ficha resumen lista para enviarme a mí).
"""

# -----------------------------------------------------------------------------
# MOCK TOOLS: TARIFARIO & GEOMEGA & SIMULATED SALES PORTAL
# -----------------------------------------------------------------------------
def geomega_check(colonia_o_cp: str) -> dict[str, Any]:
    """Herramienta GeoMega para verificar cobertura de fibra óptica Megacable en México."""
    clean = colonia_o_cp.strip().lower()
    # Mock de verificación de cobertura
    return {
        "status": "cobertura_confirmada",
        "zona": colonia_o_cp,
        "tecnologia": "Fibra Óptica FTTH (Megacable México)",
        "promocion_disponible": "Doble de velocidad gratis los primeros 6 meses + Módem Dual-Band $0 MXN costo de equipo",
        "paquetes_sugeridos": [
            {"nombre": "100 Megas Solo Internet", "precio_mxn": 450, "promocion": "Recibe 200 Megas por $450/mes"},
            {"nombre": "300 Megas Doblepack (Internet + Telefonía)", "precio_mxn": 650, "promocion": "Recibe 500 Megas por $650/mes"},
            {"nombre": "300 Megas Triplepack (Internet + TV Xview+ + Netflix)", "precio_mxn": 850, "promocion": "Xview+ HD + Netflix incluido"}
        ]
    }

def tarifario_consultar(paquete: str = "todos") -> dict[str, Any]:
    """Herramienta Tarifario Oficial Megacable México."""
    return {
        "moneda": "MXN (Pesos Mexicanos)",
        "precios_fijos": True,
        "nota_vendedor": "Precios oficiales sin descuento adicional. Usar argumentos de megas dobles e instalación gratis.",
        "catalogo": [
            {"paquete": "100 Megas Solo Internet", "precio": 450, "beneficios": "Fibra Óptica simétrica + 200 Megas promo"},
            {"paquete": "300 Megas Solo Internet", "precio": 650, "beneficios": "Fibra Óptica simétrica + 500 Megas promo"},
            {"paquete": "Triplepack Xview+ 300 Megas", "precio": 850, "beneficios": "TV en vivo 80+ canales HD + Netflix incluido"}
        ]
    }

def simular_ingreso_venta(nombre_titular: str, direccion_completa: str, paquete_elegido: str, telefono: str) -> dict[str, Any]:
    """Simulador de Portal de Ventas Megacable (Modo Sandbox de Prueba)."""
    return {
        "status": "SOLICITUD_COMPLETA_SIMULADA",
        "nota": "Venta NO enviada a producción aún. Lista para notificación a asesor.",
        "datos_capturados": {
            "cliente": nombre_titular,
            "direccion": direccion_completa,
            "paquete": paquete_elegido,
            "telefono": telefono,
            "validacion_pendiente": "Listo para enviar a Mesa de Validación"
        }
    }


# -----------------------------------------------------------------------------
# HERMES AGENT SANDBOX RUNNER
# -----------------------------------------------------------------------------
@dataclass
class HermesSandboxSession:
    session_id: str
    history: list[dict[str, str]] = field(default_factory=list)
    datos_recabados: dict[str, Any] = field(default_factory=dict)
    cobertura_validada: bool = False
    venta_simulada: bool = False

    def process_user_message(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})
        text_lower = user_text.lower()

        # 1. Regla: Verificar si es cliente nuevo o ya tiene servicio
        if any(w in text_lower for w in ["ya tengo", "ya tuve", "reconex", "pago", "soporte", "falla"]):
            reply = (
                "Entendido. Te comento que este canal es exclusivo para **nuevas contrataciones de línea nueva en México**.\n"
                "Para clientes actuales, cambios de domicilio o soporte técnico, te canalizo al número oficial de Atención a Clientes Megacable: **33 9690 0000**.\n"
                "¡Que tengas un excelente día!"
            )
            self.history.append({"role": "assistant", "content": reply})
            return reply

        # 2. Regla: Detección de Ubicación / Cobertura GeoMega
        if any(w in text_lower for w in ["cp", "código postal", "colonia", "calle", "guadalajara", "cdmx", "monterrey", "puebla", "queretaro", "leon", "ubicacion", "direccion"]):
            cov = geomega_check(user_text)
            self.cobertura_validada = True
            reply = (
                f"🗺️ **GeoMega Cobertura Confirmada en {cov['zona']}**\n\n"
                f"¡Buenas noticias! Sí contamos con **{cov['tecnologia']}** en tu zona.\n"
                f"🎁 **Promoción activa**: {cov['promocion_disponible']}.\n\n"
                f"Nuestros paquetes más populares:\n"
                f"1️⃣ **100 Megas Solo Internet**: $450 MXN/mes (¡Recibes 200 Megas los primeros meses!)\n"
                f"2️⃣ **300 Megas Doblepack**: $650 MXN/mes\n"
                f"3️⃣ **300 Megas Triplepack (Internet + TV Xview+ + Netflix)**: $850 MXN/mes\n\n"
                f"¿Cuál de estos paquetes se adapta mejor a lo que buscas en casa?"
            )
            self.history.append({"role": "assistant", "content": reply})
            return reply

        # 3. Regla: Persuasión comercial sin bajar precio
        if any(w in text_lower for w in ["caro", "descuento", "otra compañia", "pensar"]):
            reply = (
                "Comprendo totalmente tu análisis, pero considera este beneficio exclusivo de contratación nueva:\n\n"
                "✨ **Megas Dobles Gratis**: Al contratar hoy el paquete de 100 Megas ($450 MXN), Megacable te otorga el **DOBLE de velocidad (200 Megas reales)** sin costo adicional.\n"
                "📡 **Fibra Óptica Simétrica**: Sin caídas de señal cuando se conecten varios dispositivos al mismo tiempo.\n"
                "🛠️ **Costo de Equipo Módem $0 MXN**.\n\n"
                "¿Te gustaría que agendemos la instalación con esta promoción de megas dobles?"
            )
            self.history.append({"role": "assistant", "content": reply})
            return reply

        # 4. Regla: Selección de Paquete & Cierre de Datos
        if any(w in text_lower for w in ["100", "200", "300", "quiero el de", "contratar", "acepto"]):
            reply = (
                "¡Excelente elección! 🚀 Para ingresar tu solicitud de línea nueva en el portal y agendar la visita del instalador, por favor compárteme:\n\n"
                "1️⃣ Nombre completo del titular\n"
                "2️⃣ Dirección exacta (Calle, Número exterior/interior, Colonia, CP y Entre Calles)\n"
                "3️⃣ Teléfono celular de contacto"
            )
            self.history.append({"role": "assistant", "content": reply})
            return reply

        # 5. Regla: Simulación de Venta Capturada (Sin enviar a producción)
        if len(user_text.split()) >= 4 and not self.venta_simulada and self.cobertura_validada:
            sim = simular_ingreso_venta(
                nombre_titular="Cliente Sandbox de Prueba",
                direccion_completa=user_text,
                paquete_elegido="200 Megas Promo ($450 MXN)",
                telefono="3312345678"
            )
            self.venta_simulada = True
            reply = (
                "🎉 **¡DATOS RECIBIDOS CORRECTAMENTE!**\n\n"
                "--------------------------------------------\n"
                "📋 **FICHA RESUMEN DE PRUEBA DE VENTA**:\n"
                f"• Cliente: {sim['datos_capturados']['cliente']}\n"
                f"• Paquete: {sim['datos_capturados']['paquete']}\n"
                f"• Cobertura GeoMega: ✓ Confirmada Fibra Óptica\n"
                f"• Estatus Portal: SIMULADO (Prueba Sandbox exitosa)\n"
                "--------------------------------------------\n\n"
                "🔔 **NOTIFICACIÓN A ASESOR**: *Solicitud lista para enviar a la Mesa de Validación de Megacable.*"
            )
            self.history.append({"role": "assistant", "content": reply})
            return reply

        # Saludo por defecto
        reply = (
          "¡Hola! 👋 Soy Hermes Agent, Asesor Ejecutivo Oficial de Megacable México.\n"
          "Con gusto te ayudo a contratar tu servicio de Internet de alta velocidad en México.\n\n"
          "Para aplicarte las promociones especiales de **línea nueva**, ¿es la primera vez que vas a contratar en este domicilio o ya cuentas con servicio previo de Megacable?"
        )
        self.history.append({"role": "assistant", "content": reply})
        return reply


# -----------------------------------------------------------------------------
# CLI INTERACTIVE TEST RUNNER
# -----------------------------------------------------------------------------
def run_cli_sandbox():
    print("=" * 70)
    print("🤖 HERMES AGENT - MODULO SANDBOX DE PRUEBA DE VENTAS MEGACABLE MÉXICO")
    print("=" * 70)
    print("Simula que eres un prospecto mandando mensajes de prueba.")
    print("Escribe 'salir' para finalizar la sesión de prueba.\n")

    session = HermesSandboxSession(session_id="test-session-001")
    
    # Saludo inicial del bot
    print("🤖 Hermes Agent:", session.process_user_message("Hola"))

    while True:
        try:
            user_input = input("\n👤 Tu (Prospecto): ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["salir", "exit", "quit"]:
                print("\n👋 Sesión de prueba finalizada.")
                break
            
            response = session.process_user_message(user_input)
            print(f"\n🤖 Hermes Agent:\n{response}")
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Sesión interrumpida.")
            break

if __name__ == "__main__":
    run_cli_sandbox()
