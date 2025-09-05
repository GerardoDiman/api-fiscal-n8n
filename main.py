import base64
import os
import tempfile
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException
from lxml import etree
from pydantic import BaseModel

# Librería real para interactuar con los servicios del SAT
from satcfdi import Fiel

# --- SECCIÓN DE MODELOS DE DATOS (PYDANTIC) ---

class XMLRequest(BaseModel):
    xml_data: str

class DownloadRequest(BaseModel):
    rfc: str
    efirma_cer_base64: str
    efirma_key_base64: str
    efirma_password: str

# --- INICIALIZACIÓN DE LA API ---
app = FastAPI()

# --- ENDPOINTS DE LA API ---

@app.get("/test")
def test_endpoint():
    return {"mensaje": "La API de Python está viva!"}

@app.post("/parse_xml/")
async def parse_xml_endpoint(request: XMLRequest):
    # (Esta función no cambia, sigue siendo nuestro procesador de XML)
    xml_content = request.xml_data
    # Aquí iría el resto de tu código de parseo que ya funciona...
    # Por simplicidad, devolvemos un status.
    return {"status": "parseado con éxito"}

# --- ENDPOINT DE DESCARGA REAL (CORREGIDO) ---
@app.post("/descargar-xmls/")
async def descargar_xmls_endpoint(request: DownloadRequest):
    # 1. Decodificar las credenciales de la e.firma
    try:
        cer_bytes = base64.b64decode(request.efirma_cer_base64)
        key_bytes = base64.b64decode(request.efirma_key_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al decodificar la e.firma: {e}")

    # 2. Guardar las credenciales en archivos temporales
    with tempfile.NamedTemporaryFile(delete=False, suffix=".cer") as cer_file, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".key") as key_file:
        cer_file.write(cer_bytes)
        key_file.write(key_bytes)
        cer_path = cer_file.name
        key_path = key_file.name

    try:
        # 3. Cargar la e.firma usando la librería 'satcfdi'
        fiel = Fiel(cer_path=cer_path, key_path=key_path, password=request.efirma_password)
        
        # 4. Crear un servicio de portal del SAT
        portal = fiel.get_portal_cfdi()
        
        # 5. Definir rango de fechas (ej: facturas emitidas ayer)
        end_date = date.today()
        start_date = end_date - timedelta(days=1)
        
        # 6. Buscar facturas emitidas en ese rango
        facturas = portal.search_emitted(start_date=start_date, end_date=end_date)
        
        xmls_encontrados = [f.xml.decode('utf-8') for f in facturas]

        return {
            "status": f"Descarga completa. Se encontraron {len(xmls_encontrados)} facturas emitidas entre {start_date} y {end_date}.",
            "rfc": request.rfc,
            "xmls": xmls_encontrados
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la comunicación con el SAT: {e}")
    
    finally:
        # 7. Borrar siempre los archivos temporales por seguridad
        os.remove(cer_path)
        os.remove(key_path)