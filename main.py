import base64
import time
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
    return {"status": "parseado con éxito"}

@app.post("/descargar-xmls/")
async def descargar_xmls_endpoint(request: DownloadRequest):
    try:
        cer_bytes = base64.b64decode(request.efirma_cer_base64)
        key_bytes = base64.b64decode(request.efirma_key_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al decodificar la e.firma: {e}")

    try:
        signer = Signer.load(
            certificate=cer_bytes,
            key=key_bytes,
            password=request.efirma_password
        )
        
        sat_service = sat.SAT(signer=signer)
        
        end_date = date.today()
        start_date = end_date - timedelta(days=5)
        
        # Paso 1: Solicitar la descarga
        # 'descarga_masiva' no existe, así que usamos el proceso de dos pasos.
        solicitud_id = sat_service.solicita_descarga(
            start_date=start_date,
            end_date=end_date,
            download_type="received"
        )
        
        # Paso 2: Verificar el estado de la solicitud
        estado_solicitud = sat_service.verifica_solicitud_descarga(solicitud_id)
        
        # Bucle de espera. El SAT no procesa al instante, así que esperamos.
        while estado_solicitud.status == "in_progress":
            time.sleep(30) # Espera 30 segundos
            estado_solicitud = sat_service.verifica_solicitud_descarga(solicitud_id)
        
        # Obtiene la lista de paquetes disponibles para descargar
        paquetes_ids = estado_solicitud.packages_ids

        xmls_encontrados = []
        if paquetes_ids:
            for paquete_id in paquetes_ids:
                # Descarga cada paquete
                paquete_data = sat_service.descargar_paquete(paquete_id)
                for xml_content in paquete_data.cfdis:
                    xmls_encontrados.append(xml_content.decode('utf-8'))

        if not xmls_encontrados:
            return {
                "status": f"Descarga completa. No se encontraron facturas recibidas entre {start_date} y {end_date}.",
                "xmls": []
            }
        
        return {
            "status": f"Descarga completa. Se encontraron {len(xmls_encontrados)} facturas recibidas entre {start_date} y {end_date}.",
            "xmls": xmls_encontrados
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la comunicación con el SAT: {str(e)}")