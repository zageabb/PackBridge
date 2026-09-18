from packbridge import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=app.config["PACKBRIDGE_HOST"],
        port=app.config["PACKBRIDGE_PORT"],
        debug=app.config["DEBUG"],
    )
