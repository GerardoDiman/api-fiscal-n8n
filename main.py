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