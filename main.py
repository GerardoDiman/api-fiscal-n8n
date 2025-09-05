from fastapi import FastAPI, HTTPException
from lxml import etree
from pydantic import BaseModel

class XMLRequest(BaseModel):
    xml_data: str

app = FastAPI()

@app.get("/test")
def test_endpoint():
    return {"mensaje": "La API de Python está viva!"}

@app.post("/parse_xml/")
async def parse_xml_endpoint(request: XMLRequest):
    xml_content = request.xml_data
    
    NS_MAP = {
        'cfdi': 'http://www.sat.gob.mx/cfd/4',
        'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
    }

    def get_value(element, xpath):
        node = element.find(xpath, namespaces=NS_MAP)
        return node.attrib if node is not None else {}

    try:
        root = etree.fromstring(xml_content.encode('utf-8'))
        
        comprobante = root.attrib
        emisor = get_value(root, './cfdi:Emisor')
        receptor = get_value(root, './cfdi:Receptor')
        timbre = get_value(root, './/tfd:TimbreFiscalDigital')
        impuestos_data = get_value(root, './cfdi:Impuestos')
        iva = 0.0
        if 'TotalImpuestosTrasladados' in impuestos_data:
            iva = float(impuestos_data.get('TotalImpuestosTrasladados', 0.0))

        # --- AJUSTE CRÍTICO AQUÍ ---
        tipo_corto = comprobante.get('TipoDeComprobante', 'N/A').upper()
        tipo_map = {
            'I': 'INGRESO',  # Ajustado a mayúsculas para coincidir con tu Notion
            'E': 'Egreso',
            'T': 'Traslado',
            'P': 'Pago',
            'N': 'Nómina'
        }
        tipo_traducido = tipo_map.get(tipo_corto, tipo_corto)
        # --- FIN DEL AJUSTE ---

        parsed_data = {
            "uuid": timbre.get('UUID', 'N/A'),
            "fecha": comprobante.get('Fecha', 'N/A'),
            "tipo": tipo_traducido, # Usamos el valor traducido y corregido
            "emisor_rfc": emisor.get('Rfc', 'N/A'),
            "receptor_rfc": receptor.get('Rfc', 'N/A'),
            "subtotal": float(comprobante.get('SubTotal', 0.0)),
            "total": float(comprobante.get('Total', 0.0)),
            "iva_trasladado": iva
        }
        return parsed_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al parsear el XML: {str(e)}")

# Modelo para la nueva petición de descarga
class DownloadRequest(BaseModel):
    rfc: str
    # En el futuro, aquí pasaríamos las credenciales de la e.firma de forma segura

# Nuevo endpoint para iniciar la descarga
@app.post("/descargar-xmls/")
async def descargar_xmls_endpoint(request: DownloadRequest):
    rfc_cliente = request.rfc

    # --- AQUÍ IRÁ LA LÓGICA COMPLEJA DE CONEXIÓN AL SAT ---
    # 1. Autenticar con la e.firma.
    # 2. Crear la solicitud de descarga para un rango de fechas.
    # 3. Verificar periódicamente el estado de la solicitud.
    # 4. Descargar los paquetes ZIP cuando estén listos.
    # 5. Extraer todos los XML de los ZIPs.
    # ----------------------------------------------------

    # Por ahora, para construir el flujo, simularemos una respuesta exitosa
    # devolviendo el contenido de nuestro XML de prueba en una lista.
    xml_de_prueba = '<?xml version="1.0" encoding="utf-8"?><cfdi:Comprobante Version="4.0" Fecha="2024-04-29T00:00:55" SubTotal="200" Moneda="MXN" Total="199.96" TipoDeComprobante="I" xmlns:cfdi="http://www.sat.gob.mx/cfd/4"><cfdi:Emisor Rfc="EKU9003173C9" Nombre="ESCUELA KPER URGATE" RegimenFiscal="601" /><cfdi:Receptor Rfc="URE180429TM6" Nombre="UNIVERSIDAD ROBOTICA ESPAÑOLA" UsoCFDI="G01" /></cfdi:Comprobante>'

    # La API debe devolver una lista de los XMLs encontrados
    return {"status": "descarga simulada completa", "xmls": [xml_de_prueba]}