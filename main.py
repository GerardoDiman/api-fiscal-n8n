import base64
import os
import tempfile
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- LÍNEA DE IMPORTACIÓN CORREGIDA ---
from satcfdi import Fiel

# (El resto del código es idéntico al que ya tenías y es correcto)
class XMLRequest(BaseModel):
    xml_data: str

class DownloadRequest(BaseModel):
    rfc: str
    efirma_cer_base64: str
    efirma_key_base64: str
    efirma_password: str

app = FastAPI()
# ... (Aquí va el resto de tus endpoints: /test, /parse_xml/, /descargar-xmls/)
# ...

# --- ENDPOINTS DE LA API ---
@app.get("/")
def root():
    return {"status": "API en línea y funcionando"}

@app.get("/test")
def test_endpoint():
    return {"mensaje": "La API de Python está viva!"}

@app.post("/parse_xml/")
async def parse_xml_endpoint(request: XMLRequest):
    # (Aquí va tu lógica de parseo que ya funcionaba)
    # ...
    return {"status": "parseado con éxito"}

@app.post("/descargar-xmls/")
async def descargar_xmls_endpoint(request: DownloadRequest):
    try:
        cer_bytes = base64.b64decode(request.efirma_cer_base64)
        key_bytes = base64.b64decode(request.efirma_key_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al decodificar la e.firma: {e}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".cer") as cer_file, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".key") as key_file:
        cer_file.write(cer_bytes)
        key_file.write(key_bytes)
        cer_path = cer_file.name
        key_path = key_file.name

    try:
        fiel = Fiel(cer_path=cer_path, key_path=key_path, password=request.efirma_password)
        portal = fiel.get_portal_cfdi()
        end_date = date.today()
        start_date = end_date - timedelta(days=1)
        
        facturas = portal.search_received(start_date=start_date, end_date=end_date)
        
        xmls_encontrados = [f.xml.decode('utf-8') for f in facturas]

        return {
            "status": f"Descarga completa. Se encontraron {len(xmls_encontrados)} facturas recibidas entre {start_date} y {end_date}.",
            "xmls": xmls_encontrados
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la comunicación con el SAT: {e}")
    finally:
        os.remove(cer_path)
        os.remove(key_path)