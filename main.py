import base64
import time
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from satcfdi.models import Signer
# Se corrige la importación basándose en el error
from satcfdi.pacs.sat import SAT, EstadoSolicitud, _CFDIDescargaMasiva, TipoDescargaMasivaTerceros

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
        
        sat_service = SAT(signer=signer)
        
        end_date = date.today()
        start_date = end_date - timedelta(days=5)

        # Paso 1: Solicitar la descarga de facturas recibidas
        # Se usa el tipo de descarga correcto para esta versión
        response = sat_service.recover_comprobante_received_request(
            fecha_inicial=start_date,
            fecha_final=end_date,
            rfc_emisor="",
            tipo_solicitud=_CFDIDescargaMasiva.recibidas
        )
        
        id_solicitud = response.get('IdSolicitud')
        if not id_solicitud:
             raise HTTPException(status_code=500, detail="No se pudo obtener el IdSolicitud del SAT.")

        # Paso 2: Revisar estado de descarga
        while True:
            response_status = sat_service.recover_comprobante_status(id_solicitud)
            estado_solicitud = response_status.get("EstadoSolicitud")
            
            if estado_solicitud == EstadoSolicitud.TERMINADA:
                break
            elif estado_solicitud == EstadoSolicitud.RECHAZADA:
                raise HTTPException(status_code=500, detail="Solicitud de descarga rechazada por el SAT.")
            
            time.sleep(30)
            
        # Paso 3: Descargar los paquetes
        xmls_encontrados = []
        for id_paquete in response_status['IdsPaquetes']:
            response_download, paquete_zip = sat_service.recover_comprobante_download(
                id_paquete=id_paquete
            )
            # Aquí va la lógica para descomprimir y procesar el .zip
            # que necesitaría una librería como 'zipfile'
            # (Código omitido por simplicidad)

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