import base64
import os
import tempfile
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from satcfdi.models import Signer
from satcfdi.pacs import sat

class XMLRequest(BaseModel):
    xml_data: str

class DownloadRequest(BaseModel):
    rfc: str
    efirma_cer_base64: str
    efirma_key_base64: str
    efirma_password: str

app = FastAPI()

@app.get("/test")
def test_endpoint():
    return {"mensaje": "La API de Python está viva!"}

@app.post("/parse_xml/")
async def parse_xml_endpoint(request: XMLRequest):
    # (Tu lógica de parseo va aquí)
    return {"status": "parseado con éxito"}

@app.post("/descargar-xmls/")
async def descargar_xmls_endpoint(request: DownloadRequest):
    try:
        cer_bytes = base64.b64decode(request.efirma_cer_base64)
        key_bytes = base64.b64decode(request.efirma_key_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al decodificar la e.firma: {e}")

    try:
        # --- LÓGICA DE DESCARGA CON EL PARÁMETRO CORREGIDO ---
        signer = Signer.load(
            certificate=cer_bytes, # <-- CORREGIDO: de 'cer' a 'certificate'
            key=key_bytes,
            password=request.efirma_password
        )
        
        sat_service = sat.SAT(signer=signer)
        
        end_date = date.today()
        start_date = end_date - timedelta(days=5)
        
        packages = sat_service.download_received(start_date=start_date, end_date=end_date)
        
        xmls_encontrados = []
        for pkg_id, pkg_data in packages.items():
            for xml_content in pkg_data.cfdis:
                xmls_encontrados.append(xml_content.decode('utf-8'))

        return {
            "status": f"Descarga completa. Se encontraron {len(xmls_encontrados)} facturas recibidas entre {start_date} y {end_date}.",
            "xmls": xmls_encontrados
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la comunicación con el SAT: {str(e)}")