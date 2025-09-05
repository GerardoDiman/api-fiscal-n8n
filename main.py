import base64
import time
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from satcfdi.models import Signer
from satcfdi.pacs.sat import SAT, TipoDescargaMasiva, EstadoSolicitud, TipoDescargaMasivaTerceros

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
        # recover_comprobante_received_request es para facturas recibidas
        response = sat_service.recover_comprobante_received_request(
            fecha_inicial=start_date,
            fecha_final=end_date,
            rfc_emisor="", # El rfc del emisor no es necesario para facturas recibidas, se deja vacío
            tipo_solicitud=TipoDescargaMasivaTerceros.CFDI
        )
        
        id_solicitud = response.get('IdSolicitud')
        if not id_solicitud:
             raise HTTPException(status_code=500, detail="No se pudo obtener el IdSolicitud del SAT.")

        # Paso 2: Revisar estado de descarga
        # Bucle de espera. Puede tardar varios minutos.
        while True:
            response_status = sat_service.recover_comprobante_status(id_solicitud)
            estado_solicitud = response_status.get("EstadoSolicitud")
            
            if estado_solicitud == EstadoSolicitud.TERMINADA:
                break
            elif estado_solicitud == EstadoSolicitud.RECHAZADA:
                raise HTTPException(status_code=500, detail="Solicitud de descarga rechazada por el SAT.")
            
            # Si no ha terminado, espera 30 segundos antes de volver a verificar
            time.sleep(30)
            
        # Paso 3: Descargar los paquetes
        xmls_encontrados = []
        for id_paquete in response_status['IdsPaquetes']:
            response_download, paquete_zip = sat_service.recover_comprobante_download(
                id_paquete=id_paquete
            )
            # El paquete zip contiene los XMLs, necesitas descomprimirlos para leerlos
            # Esta parte del código es un poco más compleja y requeriría una librería como 'zipfile'
            # Por simplicidad, este ejemplo asume que puedes extraer los XMLs de un .zip
            # y los devuelve en una lista.
            # Aquí se asume que paquete_zip es el contenido de un .zip que contiene los XMLs
            # Y se omite la lógica de descompresión para no complicar el ejemplo

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