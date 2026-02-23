from flask import Flask, render_template_string, request, send_from_directory, redirect, session
import mysql.connector
import os
import webbrowser

app = Flask(__name__)
app.secret_key = "clave_2026"

# =========================
# LOGIN CONFIG
# =========================
USER = "admin"
PASS = "1234"

# =========================
# CONFIG DB
# =========================
db_config = {
    "host": "localhost",
    "user": "backup",
    "password": "123456",
    "database": "vigilancia",
    "connection_timeout": 5,
    "autocommit": True
}

def get_conn():
    return mysql.connector.connect(**db_config)

# =========================
# CARPETAS
# =========================
BASE = os.path.join(os.path.expanduser("~"), "Desktop", "RegistroVideovigilancia")

CARPETAS = {
    "puerta de ingreso": BASE,
    "CamaraExterior": os.path.join(BASE, "CamaraExterior")
}

# =========================
# LOGIN HTML
# =========================
LOGIN_HTML = """
<html>
<head>
<title>Login CCTV</title>
<style>
body{background:#020617;color:white;font-family:Segoe UI;display:flex;justify-content:center;align-items:center;height:100vh}
.box{background:#0f172a;padding:40px;border-radius:18px;box-shadow:0 0 40px #000;text-align:center}
input{padding:12px;width:220px;margin:10px;border:none;border-radius:8px}
button{padding:12px 25px;border:none;border-radius:8px;background:#38bdf8;font-weight:bold;cursor:pointer}
button:hover{background:#0ea5e9}
</style>
</head>
<body>
<div class="box">
<h2>🔐 LOGIN CCTV</h2>
<form method="post">
<input name="user" placeholder="Usuario"><br>
<input name="pass" type="password" placeholder="Contraseña"><br>
<button>INGRESAR</button>
</form>
</div>
</body>
</html>
"""

# =========================
# PANEL HTML
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Panel Vigilancia</title>
<meta http-equiv="refresh" content="15">
<style>
body{margin:0;background:#020617;color:white;font-family:Segoe UI}
header{background:#0f172a;padding:15px 30px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 0 20px #000}
h1{color:#38bdf8;margin:0}
.btn{padding:10px 18px;border:none;border-radius:8px;font-weight:bold;cursor:pointer}
.logout{background:#ef4444;color:white}
.stats{background:#22c55e;color:black}
.btn:hover{opacity:.8}

.panel{text-align:center;margin:20px}
button{padding:10px 18px;margin:6px;border:none;border-radius:8px;background:#38bdf8;color:black;font-weight:bold;cursor:pointer}
button:hover{background:#0ea5e9}
input{padding:7px;border-radius:6px;border:none;margin:4px}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px;padding:25px}
.card{background:#0f172a;border-radius:16px;padding:12px;box-shadow:0 0 20px #000;transition:.3s}
.card:hover{transform:translateY(-6px)}
img{width:100%;border-radius:12px;cursor:pointer}

.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.9);justify-content:center;align-items:center}
.modal img{width:80%;max-height:90%}
</style>
</head>
<body>

<header>
<h1> PANEL CCTV SATELITAL </h1>
<div>
<form action="/stats" style="display:inline">
<button class="btn stats">Estadísticas</button>
</form>

<form action="/logout" style="display:inline">
<button class="btn logout">Cerrar sesión</button>
</form>
</div>
</header>

<div class="panel">

<form method="GET">
Desde <input type="date" name="desde">
Hora <input type="time" name="hora_desde">
Hasta <input type="date" name="hasta">
Hora <input type="time" name="hora_hasta"><br>
<button>FILTRAR</button>
</form>

<form method="GET">
<button name="camara" value="puerta">Puerta</button>
<button name="camara" value="exterior">Exterior</button>
<button name="camara" value="">Todas</button>
</form>

</div>

{% if datos %}
<div class="grid">
{% for fila in datos %}
<div class="card">
<b>ID:</b> {{fila[0]}}<br>
<b>Fecha:</b> {{fila[1]}}<br>
<b>Cámara:</b> {{fila[3]}}<br><br>
<img src="/img/{{fila[2]}}" onclick="zoom(this.src)">
</div>
{% endfor %}
</div>
{% else %}
<h3 style="text-align:center">No hay registros</h3>
{% endif %}

<div class="modal" id="modal" onclick="cerrar()">
<img id="imgZoom">
</div>

<script>
function zoom(src){
document.getElementById("modal").style.display="flex"
document.getElementById("imgZoom").src=src
}
function cerrar(){
document.getElementById("modal").style.display="none"
}
</script>

</body>
</html>
"""

# =========================
# LOGIN
# =========================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form["user"]==USER and request.form["pass"]==PASS:
            session["login"]=True
            return redirect("/panel")
    return LOGIN_HTML


# =========================
# PANEL
# =========================
@app.route("/panel")
def panel():

    if not session.get("login"):
        return redirect("/")

    conn=get_conn()
    cursor=conn.cursor()

    desde=request.args.get("desde")
    hasta=request.args.get("hasta")
    hora_desde=request.args.get("hora_desde")
    hora_hasta=request.args.get("hora_hasta")
    camara=request.args.get("camara")

    query="SELECT * FROM registros WHERE 1=1"
    valores=[]

    if desde and hasta:
        query+=" AND DATE(fecha) BETWEEN %s AND %s"
        valores+=[desde,hasta]

    if hora_desde and hora_hasta:
        query+=" AND TIME(fecha) BETWEEN %s AND %s"
        valores+=[hora_desde,hora_hasta]

    if camara=="puerta":
        query+=" AND camara=%s"
        valores.append("puerta de ingreso")

    elif camara=="exterior":
        query+=" AND camara=%s"
        valores.append("CamaraExterior")

    query+=" ORDER BY fecha DESC LIMIT 200"

    cursor.execute(query,valores)
    datos=cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template_string(HTML,datos=datos)


# =========================
# ESTADISTICAS
# =========================
@app.route("/stats")
def stats():

    if not session.get("login"):
        return redirect("/")

    conn=get_conn()
    cursor=conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM registros")
    total=cursor.fetchone()[0]

    cursor.execute("SELECT camara,COUNT(*) FROM registros GROUP BY camara")
    cams=cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM registros WHERE DATE(fecha)=CURDATE()")
    hoy=cursor.fetchone()[0]

    cursor.execute("SELECT fecha FROM registros ORDER BY fecha DESC LIMIT 1")
    ultima=cursor.fetchone()

    cursor.close()
    conn.close()

    return f"""
    <body style='background:#020617;color:white;font-family:Segoe UI;text-align:center'>
    <div style='background:#0f172a;padding:40px;margin:80px auto;width:400px;border-radius:20px;box-shadow:0 0 40px black'>
    <h1 style='color:#38bdf8'>📊 Estadísticas</h1>

    Total detecciones<br><h2>{total}</h2><hr>
    Detectadas hoy<br><h2>{hoy}</h2><hr>
    Última detección<br><b>{ultima}</b><hr>

    <h3>Por cámara</h3>
    {"".join([f"{c[0]} → {c[1]}<br>" for c in cams])}

    <br><br>
    <a href='/panel' style='color:#38bdf8;font-weight:bold'>⬅ Volver</a>
    </div>
    """


# =========================
# IMAGEN SEGURA
# =========================
@app.route("/img/<nombre>")
def img(nombre):

    if not session.get("login"):
        return redirect("/")

    conn=get_conn()
    cursor=conn.cursor()
    cursor.execute("SELECT camara FROM registros WHERE imagen=%s",(nombre,))
    resultado=cursor.fetchone()
    cursor.close()
    conn.close()

    if not resultado:
        return "No encontrada"

    carpeta=CARPETAS.get(resultado[0])
    return send_from_directory(carpeta,nombre)


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================
# START
# =========================
if __name__=="__main__":
    webbrowser.open("http://127.0.0.1:5000")
    app.run(threaded=True)
