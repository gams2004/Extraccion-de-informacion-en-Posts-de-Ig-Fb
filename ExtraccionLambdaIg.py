"""
@Author: Gabriel Martín
"""
from apify_client import ApifyClient
import sys
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import json
import re
import os

#Permite al sistema imprimir caracteres especiales
sys.stdout.reconfigure(encoding='utf-8')

#uri de conexión a Mongo (ingresa tu propia uri)
mongoUri = os.environ["MONGOURI"]
    
#Apify token (Ingresa el token de tu cuenta de Apify)
apifyToken = os.environ["APIFYKEY"]

#Declaramos token de Apify 
clientApify = ApifyClient(apifyToken)

# Crea un nuevo cliente y se contecta al servidor
clientMongo = MongoClient(mongoUri, server_api=ServerApi('1'))

# Se conecta a la base de datos
db = clientMongo.datosRedesSociales

# Utilizamos la colección "datos"
collection = db["Entries"]

# Función para guardar datos en MongoDB desde Python, recibe una lista de objetos json
def guardar_datos_en_mongo(datos):
    try:
        for obj in datos:
            # Insertar el objeto JSON en la base de datos
            collection.insert_one(obj)
        
        return 'Datos guardados correctamente en MongoDB.'

    except Exception as e:
        return 'Error al guardar los datos en MongoDB:', e 

#Función que extrae los hashtags y menciones de un texto    
def extract_hashtags_mentions(text):
    # Define los patrones de las expresiones regulares para hashtags y menciones
    hashtag_pattern = r'#(\w+)'  # Hashtags: palabras que comienzan con '#'
    mention_pattern = r'@(\w+)'  # Menciones: palabras que comienzan con '@'
    
    # Encuentra todos los hashtags y menciones en el texto
    hashtags = re.findall(hashtag_pattern, text)
    mentions = re.findall(mention_pattern, text)
    
    # Devuelve un diccionario con los hashtags y menciones
    result = {
        "hashtags": hashtags,
        "mentions": mentions
    }
    
    return result
    
#Función que extrae los primeros 50 comentarios de un post dado
def extraccion_comentarios_ig(padre):
    run_input={
        "addParentData": False,
        "directUrls": [
            str(padre.get("url"))
        ],
        "enhanceUserSearchWithFacebookPage": False,
        "isUserTaggedFeedURL": False,
        "resultsLimit": 1,
        "resultsType": "comments",
        "searchType": "hashtag"
    }

    # Run the Actor and wait for it to finish
    run = clientApify.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)

    #Lista donde se guardarán los comentarios
    datos = []

    # Fetch and print Actor results from the run's dataset (if there are any)
    for item in clientApify.dataset(run["defaultDatasetId"]).iterate_items():
        datos_e = extract_hashtags_mentions(item.get("text"))
        # Convierte los datos en un objeto JSON
        objeto_json = {
            "type":"comentario de Instagram",
            "socialNetwork": "instagram",
            "content": item.get("text"),
            "usernameSocialNetwork": item.get("ownerUsername"),
            "dateCreated": str(item.get("timestamp")),
            "dateQuery":str(datetime.now()),
            "location": "null",
            "usersMentioned": datos_e.get("mentions"),
            "properties":{
                "postId":item.get("id"),
                "postURL":"No contiene",
                "mediaURL":"No contiene",
                "likes":item.get("likesCount"),
                "comments":"No aplica"
            },
            "_parentEntryID":padre.get("id"),
            "hashtags": datos_e.get('hashtags')
        }
        datos.append(objeto_json)
    
    result = {"response": guardar_datos_en_mongo(datos)}
    return result


#Función lambda que extrae la información de un usuario de Instagram 
def lambda_handler(event, context): 

    # Recogemos el nombre del usuario de instagram a buscar de event[user]
    username = event.get("username")

    # Formato fecha = YYYY-MM-DD
    date_until_search = event.get("date_until_search")

    # Obtenemos el número máximo de posts a buscar
    max_posts = event.get("max_posts")
    
    if not username:
        return {"response": "No se proporciona nombre de usuario"}
    
    if not date_until_search:
        date_until_search = "2023-12-24"
    if not max_posts:
        max_posts=10


    run_input = {
        "addParentData": False,
        "directUrls": [
        "https://www.instagram.com/"+username+"/",
        ],
        "enhanceUserSearchWithFacebookPage": False,
        "isUserTaggedFeedURL": False,
        "onlyPostsNewerThan": date_until_search,
        "resultsLimit": max_posts,
        "resultsType": "posts"
    }

    # Corre el actor que extraerá la información
    run = clientApify.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)

    datos = []
    for item in clientApify.dataset(run["defaultDatasetId"]).iterate_items():
        tipo = item.get("type")

        if tipo == "Video":
            mediaURL = [item.get("videoUrl")]

        if tipo == "Sidecar":
            mediaURL = item.get("images")

        if tipo == "Image":
            mediaURL = [item.get("displayUrl")]

        # Convierte los datos en un objeto JSON
        objeto_json = {
            "type":"post de Instagram",
            "socialNetwork": "instagram",
            "content": item.get("caption"),
            "usernameSocialNetwork": username,
            "dateCreated": str(item.get("timestamp")),
            "dateQuery":str(datetime.now()),
            "location": item.get("locationName"),
            "usersMentioned": item.get("mentions"),
            "properties":{
                "postId":item.get("id"),
                "postURL":item.get("url"),
                "mediaURL":mediaURL,
                "likes":item.get("likesCount"),
                "comments":item.get("commentsCount")
            },
            "_parentEntryID":item.get("ownerId"),
            "hashtags": item.get('hashtags')
        }
        extraccion_comentarios_ig(item)
        datos.append(objeto_json)
    
    result = {"response": guardar_datos_en_mongo(datos)}
    return result

#Evento con los parámetros de búsqueda
event={
    "username":"gustavopetrourrego",
    "date_until_search":"2023-12-24",
    "max_posts": 3
}

print(lambda_handler(event, None))