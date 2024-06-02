"""SpotiLytics app that returns data from spotify endpoint API"""

import os
import json
import datetime
import requests
from uuid import uuid4
from urllib import parse
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template, redirect, session

app = Flask(__name__)
app.secret_key = str(uuid4())

load_dotenv()

ClientId = os.getenv("ClientId")
ClientSecret = os.getenv("ClientSecret")
RedirectUri = "http://localhost:5000/callback"
AuthUrl = "https://accounts.spotify.com/authorize"
TokenUrl = "https://accounts.spotify.com/api/token"
ApiUrl = "https://api.spotify.com/v1/me"


@app.route("/")
def index():
    """
    This function returns a welcome message with a link to login with Spotify.

    Returns:
        str: The welcome message with the login link.
    """

    return "Welcome to SpotiLytics <a href=/login> Login with Spotify</a> <br>\
            Check your <a href=/playlists> playlists</a> <br> \
            Check your <a href= /profile> profile</a>"


@app.route("/login")
def login():
    """
    Redirects the user to the Spotify authorization page for login.

    Returns:
        A redirect response to the Spotify authorization page.
    """

    scope = "user-read-private user-read-email playlist-read-private"
    params = {
        "client_id": ClientId,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": RedirectUri,
        "show_dialog": True
    }

    auth_url = f"{AuthUrl}?{parse.urlencode(params)}"
    return redirect(auth_url)


@app.route("/callback")
def callback():
    """
    Callback function for handling the response from the authorization server.

    Returns:
        A redirect to the "/playlists" endpoint if the authorization code is present in the request arguments.
        Otherwise, returns a JSON response with an error message if the "error" parameter is present in the request arguments.
    """

    if "error" in request.args:
        return jsonify({"error": request.args["error"]})

    if "code" in request.args:
        body = {
            "code": request.args["code"],
            "grant_type": "authorization_code",
            "redirect_uri": RedirectUri,
            "client_id": ClientId,
            "client_secret": ClientSecret
        }

        response = requests.post(TokenUrl, data=body)
        token = response.json()
        session["access_token"] = token["access_token"]
        session["refresh_token"] = token["refresh_token"]
        session["expires_at"] = datetime.datetime.now().timestamp() + \
            token["expires_in"]

        return redirect("/")


@app.route("/playlists")
def get_playlists():
    """
    Retrieves playlists from the Spotify API.

    Returns:
        A JSON response containing the playlists.
    """

    if "access_token" not in session:
        return redirect("/login")

    if datetime.datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh-token")

    headers = {
        "Authorization": "Bearer " + session["access_token"]
    }
    response = requests.get(
        ApiUrl + "/playlists?offset=0&limit=20", headers=headers)
    data = response.json()
    for playlist in data["items"]:
        name = playlist["name"]
        display_name = playlist["owner"]["display_name"]
        total_tracks = playlist["tracks"]["total"]
        print("Owner:", playlist["owner"]["display_name"])
        print("Playlist name:", playlist["name"])
        print("Total tracks:", playlist["tracks"]["total"])

    return jsonify({
        "Playlist name": name,
        "Owner": display_name,
        "Total tracks": total_tracks
    })


@app.route("/profile")
def get_profile():
    """
    Retrieves the current user's profile from the API.

    Returns:
        A JSON response containing the user profile.
    """
    if "access_token" not in session:
        return redirect("/login")

    if datetime.datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh-token")
    headers = {
        "Authorization": "Bearer " + session["access_token"]
    }
    response = requests.get(ApiUrl, headers=headers)
    profile = response.json()

    return jsonify(profile)


@app.route("/refresh-token")
def refresh_token():
    """
    Refreshes the access token if it has expired.

    Returns:
        A redirect to the "/playlists" endpoint if the access token has been successfully refreshed.
        Otherwise, returns a redirect to the "/login" endpoint.
    """

    if "refresh_token" not in session:
        return redirect("/login")

    if datetime.datetime.now().timestamp() > session["expires_at"]:
        body = {
            "grant_type": "refresh_token",
            "refresh_token": session["refresh_token"],
            "client_id": ClientId,
            "client_secret": ClientSecret
        }
        response = requests.post(TokenUrl, data=body)
        new_token = response.json()

        session["access_token"] = new_token["access_token"]
        session["expires_at"] = datetime.datetime.now().timestamp() + \
            new_token["expires_in"]
        return redirect("/playlists")


if __name__ == "__main__":

    """ Main Function """
    app.run(host='0.0.0.0', debug=True, port=5000)