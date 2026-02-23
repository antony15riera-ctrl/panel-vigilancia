import cv2
import numpy as np
from datetime import datetime
from urllib.parse import quote
import os
import time
import mysql.connector

# ==============================
# CONEXION MYSQL
# ==============================
conexion = mysql.connector.connect(
    host="localhost",
    user="backup",
    password="123456",
    database="vigilancia"
)
cursor = conexion.cursor()
print("✅ Conectado a MySQL")

# ==============================
# CARPETAS
# ==============================
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
BASE = os.path.join(desktop, "RegistroVideovigilancia")

PUERTA_FOLDER = BASE
EXTERIOR_FOLDER = os.path.join(BASE, "CamaraExterior")

os.makedirs(PUERTA_FOLDER, exist_ok=True)
os.makedirs(EXTERIOR_FOLDER, exist_ok=True)

# ==============================
# MODELO IA
# ==============================
model_folder = r"C:\Users\Jhoan\modelos"
proto = os.path.join(model_folder,"MobileNetSSD_deploy.prototxt")
model = os.path.join(model_folder,"MobileNetSSD_deploy.caffemodel")

net = cv2.dnn.readNetFromCaffe(proto, model)

CLASSES = ["background","aeroplane","bicycle","bird","boat",
           "bottle","bus","car","cat","chair","cow","diningtable",
           "dog","horse","motorbike","person","pottedplant",
           "sheep","sofa","train","tvmonitor"]

# ==============================
# CAMARAS
# ==============================
cams = [
    {
        "nombre":"puerta de ingreso",
        "folder":PUERTA_FOLDER,
        "user":"admin",
        "password":"Sat2025*/",
        "ip":"172.16.10.32",
        "puerto":554,
        "path":"/Streaming/Channels/101"
    },
    {
        "nombre":"CamaraExterior",
        "folder":EXTERIOR_FOLDER,
        "user":"admin",
        "password":"@202@3#$kinder$%",
        "ip":"172.16.10.62",
        "puerto":554,
        "path":"/Streaming/Channels/101"
    }
]

# ==============================
# FUNCION PARA CREAR URL RTSP SEGURA
# ==============================
def generar_rtsp(cam):
    user = quote(cam["user"], safe='')
    passwd = quote(cam["password"], safe='')  # codifica todos los caracteres especiales
    return f"rtsp://{user}:{passwd}@{cam['ip']}:{cam['puerto']}{cam['path']}"

# ==============================
# INICIALIZAR CAPTURAS
# ==============================
caps = []
for cam in cams:
    url = generar_rtsp(cam)
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    caps.append(cap)

last = [0]*len(cams)
intervalo = 5

# ==============================
# LOOP PRINCIPAL MEJORADO
# ==============================
try:
    while True:
        for i, cap in enumerate(caps):
            try:
                if not cap.isOpened():
                    # intenta reconectar si falla
                    url = generar_rtsp(cams[i])
                    cap.release()
                    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                    caps[i] = cap
                    time.sleep(1)
                    print(f"🔄 Reconectando {cams[i]['nombre']}")
                    continue

                ret, frame = cap.read()
                if not ret:
                    print(f"⚠️ No se recibió frame de {cams[i]['nombre']}")
                    # intenta reconectar inmediatamente
                    cap.release()
                    url = generar_rtsp(cams[i])
                    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                    caps[i] = cap
                    continue

                # detección IA
                (h, w) = frame.shape[:2]
                blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300,300)), 0.007843, (300,300), 127.5)
                net.setInput(blob)
                detections = net.forward()

                personas = 0
                for j in range(detections.shape[2]):
                    conf = detections[0,0,j,2]
                    idx = int(detections[0,0,j,1])
                    if conf > 0.5 and CLASSES[idx]=="person":
                        personas += 1
                        box = detections[0,0,j,3:7]*np.array([w,h,w,h])
                        (x1,y1,x2,y2) = box.astype("int")
                        cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)

                ahora = time.time()
                if personas>0 and ahora-last[i]>intervalo:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    hora = datetime.now().strftime("%H-%M-%S")
                    nombre = f"persona_{hora}.jpg"
                    ruta = os.path.join(cams[i]["folder"], nombre)

                    cv2.imwrite(ruta, frame)
                    sql = "INSERT INTO registros (fecha, imagen, camara) VALUES (%s,%s,%s)"
                    cursor.execute(sql,(fecha,nombre,cams[i]["nombre"]))
                    conexion.commit()
                    print("📸", cams[i]["nombre"], nombre)
                    last[i]=ahora

                vista = cv2.resize(frame, (480,270))
                cv2.imshow(cams[i]["nombre"], vista)

            except Exception as e:
                print(f"❌ Error con {cams[i]['nombre']}: {e}")
                continue  # no bloquea la ejecución de otras cámaras

        if cv2.waitKey(1)==27:  # tecla ESC para salir
            break

finally:
    for cap in caps:
        cap.release()
    cv2.destroyAllWindows()
    cursor.close()
    conexion.close()
    print("🛑 Conexión cerrada y cámaras liberadas")
