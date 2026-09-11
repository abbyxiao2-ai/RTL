import os
from functools import wraps
from flask import Flask, flash, redirect, render_template, request, session
from cs50 import SQL
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure upload directory with reliable absolute path
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.secret_key = "supersecretkey"

db = SQL("sqlite:///data.db")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/")
@login_required
def index():
    id = session.get("user_id")
    rows = db.execute("SELECT username FROM users WHERE id = ?", id)

    if len(rows) != 1:
        session.clear()
        return redirect("/login")

    username = rows[0]["username"]
    contacts = db.execute("SELECT * FROM contacts WHERE user_id = ?", id)
    return render_template("hello.html", name=username, contacts=contacts)


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Must provide username and password", "error")
            return render_template("login.html")

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 1 or not check_password_hash(rows[0]["password_hash"], password):
            flash("Invalid username and/or password", "error")
            return render_template("login.html")
        else:
            session["user_id"] = rows[0]["id"]
            flash("Welcome!", "success")
            return redirect("/")
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            flash("Must Provide Username and Password", "error")
            return render_template("register.html")

        elif len(db.execute("SELECT * FROM users WHERE username = ?", username)) != 0:
            flash("Username Already Taken", "error")
            return render_template("register.html")

        elif password != confirmation:
            flash("Password and Confirmation Must Match", "error")
            return render_template("register.html")

        else:
            hash = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users (username, password_hash) VALUES (?,?)", username, hash)
            flash("Registered!", "success")
            return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/addppl", methods=["GET", "POST"])
@login_required
def addppl():
    if request.method == "GET":
        return render_template("addppl.html")
    else:
        name = request.form.get("name")
        if not name:
            flash("Must input a name", "error")
            return render_template("addppl.html")

        pronunciation = request.form.get("pronunciation") or ""
        relationship = request.form.get("relationship") or ""
        remark = request.form.get("remark") or ""
        year = request.form.get("year") or ""
        month = request.form.get("month") or ""
        day = request.form.get("day") or ""
        hobbies = request.form.get("hobbies") or ""
        personalities = request.form.get("personalities") or ""
        gifts = request.form.get("gifts") or ""
        number = request.form.get("phonenumber") or ""

        # Safe File Handling
        filenames = []
        if "images" in request.files:
            uploaded_files = request.files.getlist("images")
            for file in uploaded_files:
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    if filename:
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        filenames.append(filename)
        image_string = ",".join(filenames) if filenames else ""


        audios = []
        if "audio" in request.files:
            uploaded_audio = request.files.getlist("audio")
            for audio in uploaded_audio:
                if audio and audio.filename != '':
                    audioname = secure_filename(audio.filename)
                    if audioname:
                        audiopath = os.path.join(app.config['UPLOAD_FOLDER'], audioname)
                        audio.save(audiopath)
                        audios.append(audioname)
        audio = ",".join(audios) if audios else ""


        db.execute(
            """
            INSERT INTO contacts (
                user_id, name, pronunciation, relationship, remark, 
                birth_day, birth_month, birth_year, hobbies, 
                personalities, gifts, images, phonenumber, audio_path
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            session["user_id"], name, pronunciation, relationship, remark,
            day, month, year, hobbies, personalities, gifts, image_string, number, audio
        )

        flash(f"Successfully Remembered '{name}'!", "success")
        return redirect("/")


@app.route("/ppl/<int:person_id>", methods=["GET"])
@login_required
def ppl(person_id):
    rows = db.execute(
        "SELECT * FROM contacts WHERE id = ? AND user_id = ?",
        person_id, session["user_id"]
    )

    if len(rows) != 1:
        flash("Person not found!", "error")
        return redirect("/")

    person = rows[0]
    return render_template("ppl.html", person=person)




@app.route("/edit/<int:person_id>", methods=["GET", "POST"])
@login_required
def edit(person_id):
    if request.method == "GET":
        rows = db.execute(
            "SELECT * FROM contacts WHERE id = ? AND user_id = ?", person_id, session["user_id"]
        )
        if len(rows) != 1:
            flash("Person not found!", "error")
            return redirect("/")
        return render_template("edit.html", person=rows[0])
    else:
        if not request.form.get("name"):
            flash("Must input a name", "error")
            return redirect(f"/ppl/{person_id}")


        existing = db.execute("SELECT images FROM contacts WHERE id = ? AND user_id = ?", person_id, session["user_id"])
        existing_string = existing[0]["images"] if existing and existing[0]["images"] else ""
        filenames = []
        if "images" in request.files:
            uploaded_files = request.files.getlist("images")
            for file in uploaded_files:
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    if filename:
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        filenames.append(filename)

        new_upload_string = ",".join(filenames)

        if existing_string and new_upload_string:
            image_string = existing_string + "," + new_upload_string  # Combine both!
        elif existing_string:
            image_string = existing_string
        else:
            image_string = new_upload_string

#audio saving
        audio = db.execute("SELECT audio_path FROM contacts WHERE id = ? AND user_id = ?", person_id, session["user_id"])
        existaudio = audio[0]["audio_path"] if audio and audio[0]["audio_path"] else ""
        audiofiles = []
        if "audio" in request.files:
            recorded = request.files.getlist("audio")
            for audios in recorded:
                if audios and audios.filename != '':
                    audiofile = secure_filename(audios.filename)
                    if audiofile:
                        audios.save(os.path.join(app.config['UPLOAD_FOLDER'], audiofile))
                        audiofiles.append(audiofile)


        new_audio_string = ",".join(audiofiles)


        if new_audio_string:
            new_audio = new_audio_string
        else:
            new_audio = existaudio


        
        db.execute(
            """
            UPDATE contacts 
            SET name = ?, pronunciation = ?, phonenumber = ?, relationship = ?, 
                remark = ?, birth_year = ?, birth_month = ?, birth_day = ?, 
                hobbies = ?, personalities = ?, gifts = ?, images = ?, audio_path = ?
            WHERE id = ? AND user_id = ?
            """,
            request.form.get("name"),
            request.form.get("pronunciation") or "",
            request.form.get("phonenumber") or "",
            request.form.get("relationship") or "",
            request.form.get("remark") or "",
            request.form.get("year") or "",
            request.form.get("month") or "",
            request.form.get("day") or "",
            request.form.get("hobbies") or "",
            request.form.get("personalities") or "",
            request.form.get("gifts") or "",
            image_string,
            new_audio,
            person_id,
            session["user_id"]
        )
        return redirect(f"/ppl/{person_id}")


@app.route("/delete/<int:person_id>", methods=["POST"])
@login_required
def delete(person_id):
    rows = db.execute("SELECT name FROM contacts WHERE id = ? AND user_id = ?", person_id, session["user_id"])
    if rows:
        name = rows[0]["name"]
        flash(f"Successfully deleted {name}!", "success")
        db.execute("DELETE FROM contacts WHERE id = ? AND user_id = ?", person_id, session["user_id"])
        return redirect("/")
    else:
        return redirect("/")


@app.route("/delete-photo/<int:person_id>", methods=["POST"])
@login_required
def delete_photo(person_id):
    filename_to_delete = request.form.get("filename")
    
    if not filename_to_delete:
        flash("Invalid file", "error")
        return redirect("/")
    else:
        rows = db.execute("SELECT images FROM contacts WHERE id = ? AND user_id = ?", person_id, session["user_id"])
        if len(rows) == 1 and rows[0]["images"]:
            image_list = rows[0]["images"].split(",")
            if filename_to_delete in image_list:
                image_list.remove(filename_to_delete)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_to_delete)
                if os.path.exists(file_path):
                    os.remove(file_path)
            new_image_string = ",".join(image_list)
            db.execute("UPDATE contacts SET images = ? WHERE id = ? AND user_id = ?", new_image_string, person_id, session["user_id"])
    
    return redirect(f"/ppl/{person_id}")


@app.route("/delete_audio/<int:person_id>", methods=["POST"])
@login_required
def delete_audio(person_id):
    db.execute("UPDATE contacts SET audio_path = ? WHERE id = ? AND user_id = ?","", person_id, session["user_id"])
    
    return redirect(f"/ppl/{person_id}")



if __name__ == "__main__":
    app.run(debug=False)