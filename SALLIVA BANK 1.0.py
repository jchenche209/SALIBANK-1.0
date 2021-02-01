#Application for the SALIBANK prototype.

# ---------------------------------- Trouble shooting ----------------------------
#printer access denied: terminal -> "sudo chmod 0666 /dev/usb/lp0" before running program


# ---------------------------------- Libraries ----------------------------

from tkinter import *
from tkinter import messagebox

from PIL import ImageTk,Image #for images

import datetime #for date and time
import time 

import shutil   #For copy and moving files

import sqlite3   #Database

import barcode   # Barcodes
from barcode.writer import ImageWriter
from barcode import generate

from brother_ql.conversion import convert   #printer control
from brother_ql.backends.helpers import send
from brother_ql.raster import BrotherQLRaster

import serial # comunication with Arduinos

import os # Not always needed
os.chdir("/home/pi/Desktop/PROGRAM")

# ---------------------------------- Creating main window ----------------------------
root = Tk()
root.title("SALIBANK 1.0")
root.iconbitmap("@/home/pi/Desktop/PROGRAM/SALIBANKICO.xbm") # Use .ico for most OS, if doesn't work use .xbm
root.geometry("800x480")
screen_width = 800
screen_height = 480
root.config(cursor="none")

# ---------------------------------- Variables and Parameters ----------------------------
#Serial info
# uC1/uC2: Control unit 1 and 2
# printeraddress: Printer port

uc1 = "/dev/ttyUSB0" 
uc2 = ""
printeraddress = "/dev/usb/lp0"

# Settings
operatorID = "CHZH0950719007"
adminID = "CHZH0950719008"
kit_reserve = 200   #number of available kits
storedsample_count = 0 #number of sample contained
storedsample_limit = 200

#Database paths: origin: default db / destination: target db for collection / backup: backup db
db_origin = './registro.db'
db_destination = './registro_copy.db'
db_backup = './registro_backup.db'

#Variables
userCIP = StringVar() #user CIP
entryvar = StringVar() #Login entry
accesslevel = IntVar()
accesslevel.set(0)# level of the user, 0 for normal user, 1 for operators, 2 for administrator.
get_kit_enabled = IntVar() #For kit deposition
inloginscreen = False #For screensaver timer
ticketinfo = StringVar() # For barcode
sample_detected = IntVar()
sample_detected.set(0) #0: default, 1: sample detected
saver_back = None   #Counter to start screensaver.
saver_back_timer = 120000   #time to take for screensaver to pop back 2min = 120000

# ---------------------------- Database setup sqlite3: registro.db ----------------------------

# Create/connect to database
conn = sqlite3.connect('registro.db')

# Create cursor (call everytime for any action)
c = conn.cursor()

# Create table (in sqlite3, each record has a unique id "oid")
# CIP, :access_date, :kit_pick, :submit, :submit_date
c.execute( """ CREATE TABLE if not exists registro (
            CIP text,
            acess_date text,
            kit_pick integer,
            submit text ,
            submit_date text)
            """)

# Commit Changes
conn.commit()

# Close Connection
conn.close()

# ---------------------------------- Arduino communication ----------------------------

# Only considered 1 arduino, modify accordingly.

arduinoData1 = serial.Serial(uc1,9600)    # add for each arduino and change 'com3' to corresponding (see ArduinoIDE).
### arduinoData1 = serial.Seria1(uc1,9600)

def ard_depositkit():    # Signaling for kit deposition.
    arduinoData1.write(str.encode('0'))
    time.sleep(1)
    while arduinoData1.inWaiting() == 0:
        time.sleep(1);
        

def ard_opensubmit():    # Signaling to enable sample submit and wait for deposited signal, check every 1s, for 6s
    arduinoData1.write(str.encode('1'))
    time.sleep(1)
    while (arduinoData1.inWaiting() == 0) and (a < 6):
        a += 1
        time.sleep(1);

    global sample_detected   
    if arduinoData1.inWaiting() != 0:
        print("uC signal detected")
        sample_detected.set(1)
    else:
        print("Fail to detect uC signal")
        sample_detected.set(0)


# ---------------------------------- functions ----------------------------

def raise_frame(frame):    #alias used in some functions
    frame.tkraise()


def screensaver_pop_back():    # Go screensaver
    print("screensaver is up")
    login_entry.delete(0,'end')
    entryvar.set('')
    
    global inloginscreen
    inloginscreen = False
    raise_frame(f_saver)



def go_login():    # From screensaver or quitting sesion.
    global inloginscreen
    inloginscreen = True
    raise_frame(f_login)
    
    global saver_back
    saver_back = root.after(saver_back_timer, screensaver_pop_back)


def login():    # Login credential check
    
    #kill screensave timer
    global saver_back
    root.after_cancel(saver_back)
    
    #Check if login string is correct
    if (len(entryvar.get()) < 24 or len(entryvar.get())> 25):
        login_entry.delete(0,'end')
        entryvar.set('')
        messagebox.showwarning("SALIBANK 1.0","Identificación errónea, por favor identifiquese con su tarjeta sanitaria individual")
        saver_back = root.after(saver_back_timer, screensaver_pop_back)
    
    else:
        userCIP.set(entryvar.get()[6:20])
        
        #Config user access level and modify screen display options
        if(userCIP.get()== adminID):
            accesslevel.set(2);
            header = "Admin | "
        elif(userCIP.get() == operatorID):
            accesslevel.set(1)
            header = "Operador | "
        else:
            accesslevel.set(0)
            header = "Usuario CIP| "
            
        if(accesslevel.get() == 0):
            query_restock.grid_forget()
            query_emptystorage.grid_forget()
            query_delete.grid_forget()
            query_copy.grid_forget()
        else:
            query_restock.grid(row = 2, column = 0, sticky="news", padx=10, pady=10) #Copy paste to func: login()
            query_emptystorage.grid(row = 2, column = 1, sticky="news", padx=10, pady=10) #Copy paste to func: login()
            query_copy.grid(row = 2, column = 2, sticky="news", padx=10, pady=10) #Copy paste to func: login()
            query_delete.grid(row = 2, column = 3, sticky="news", padx=10, pady=10) #Copy paste to func: login()

        for userdisplay in (main_userdisplay, getkit_userdisplay ,submit_userdisplay ,query_userdisplay, help_userdisplay):
            userdisplay['text'] = header + userCIP.get()

        if(accesslevel.get() != 2):
            register_db();
        
        login_entry.delete(0,'end')
        entryvar.set('')
        global inloginscreen
        inloginscreen = False        
        raise_frame(f_main);


def login_return(self):    # placeholder func, disables login input beside login screen
    if(inloginscreen == True):    # Check if in login screen
        login()    
    else:
        entryvar.set('')
        login_entry.delete(0,'end')



def quit_sesion():    #quit sessions messagebox
    response = messagebox.askyesno("SALIBANK 1.0","¿Estás seguro de finalizar su sesión?")
    if response == 1:
        #Reset buttons atatus
        main_getkit["state"]= NORMAL
        main_submitkit["state"]= NORMAL
        go_login();


def go_getkit():
    if kit_reserve == 0:
       messagebox.showwarning("SALIBANK 1.0","Lo sentimos mucho, en este momento SALIBANK no dispone de mas kits")
    else:
        raise_frame(f_getkit)
  
def quitgetkit():    #From direct exit or after reclaming kit  
    getkit_checkbox.deselect()
    getkit_accept["state"]= DISABLED
    raise_frame(f_main)


def enablegetkit():
    if (get_kit_enabled.get() == 1):
        getkit_accept["state"]= NORMAL
    else:
        getkit_accept["state"]= DISABLED


def claimkit():
    main_getkit["state"]= DISABLED
    
    print("informado a uC para depositar kit")
    ard_depositkit()
    display_notification(notification_kitdeposited)
    update_kitpick_register()
    global kit_reserve
    kit_reserve -= 1
    print("kit_reserve" + str(kit_reserve))
    root.after(4000,quitgetkit)

def go_submit():
    if (storedsample_count >= storedsample_limit):
       messagebox.showwarning("SALIBANK 1.0","Lo sentimos mucho, este equipo ya no puede albergar mas muestras")
    else:
        raise_frame(f_submit)
   
def printticket():
    #create ticketinfo
    ticketinfo.set(str(time.strftime('%m%d%H%M%S')+ userCIP.get()[0:11]))

    display_notification(notification_printticket)
    
    #generate barcode png:
    barcode_class = barcode.get_barcode_class('code128')
    finalcode = barcode_class(ticketinfo.get(), writer=ImageWriter())
    fullname = finalcode.save('barcode')
    bardcode_img = Image.open('./barcode.png')
    bardcode_img = bardcode_img.resize((991,306))
    
    #send ocmmand to printer
    backend = 'linux_kernel'    # 'pyusb', 'linux_kernal', 'network'
    model = 'QL-700' # your printer model.
    global printeraddress
    printer = printeraddress
    
    qlr = BrotherQLRaster(model)
    qlr.exception_on_warning = True

    instructions = convert(
        qlr=qlr, 
        images=[bardcode_img],    #  Takes a list of file names or PIL objects.
        label='62',         # Corresponding label
        rotate='auto',    # 'Auto', '0', '90', '270'
        threshold=70.0,    # Black and white threshold in percent.
        dither=False, 
        compress=False, 
        red=False,    # Only True if using Red/Black 62 mm label tape.
        dpi_600=False, 
        lq=False,    # True for low quality.
        no_cut=False
        )

    send(instructions=instructions, printer_identifier=printer, backend_identifier=backend, blocking=True)
    #finalize printing
    
    return_submit()
    
def submitsample():
    
    response = messagebox.askokcancel("SALIVA BANK 1.0","Asegure de que su muestra tenga el identificador pegado antes de depositar. ¿desea continuar con el proceso de depósito?")

    if response == 1:
         
        display_notification(notification_submittip)

        print("enable sample disposal")       
        ard_opensubmit()
                
        if (sample_detected.get() == 1):
            print("success")
            update_submit_register()
            main_submitkit["state"]= DISABLED
            display_notification(notification_submitsuccess)

            root.after(4000,exit_submit)
        else:
            print("failed")
            display_notification(notification_submitfailed);

            root.after(4000,return_submit)
     

def return_submit():
    f_submit.tkraise()
    
def exit_submit():
    f_main.tkraise()

def go_query():
    print("accessing query")
    raise_frame(f_query)
    query() # Call the query fuction to search and display

def exit_query():
    raise_frame(f_main)
    query_useinfo.delete(0.0,END)


# register sesion to database
def register_db():
    # Create/connect to database
    conn = sqlite3.connect('registro.db')
    # Create cursor (call everytime for any action)
    c = conn.cursor()
    # Insert entry to table
    c.execute("INSERT INTO registro VALUES(:cip, :access_date, :kit_pick, :submit, :submit_date)",
            {

                'cip': userCIP.get(),
                'access_date':time.strftime('%Y/%m/%d %H:%M:%S'),
                'kit_pick': 0,
                'submit': 0,
                'submit_date':0
            }
              )
    # Commit Changes
    conn.commit()
    # Close Connection
    conn.close()

# Update kit_pick
def update_kitpick_register():
    # Create/connect to database
    conn = sqlite3.connect('registro.db')
    # Create cursor (call everytime for any action)
    c = conn.cursor()

    # update kit_pick
    c.execute("UPDATE registro SET kit_pick = kit_pick + 1 WHERE oid = (SELECT MAX(oid) FROM registro)")
    
    # Commit Changes
    conn.commit()
    # Close Connection
    conn.close()

# Update submit info
def update_submit_register():
    # Create/connect to database
    conn = sqlite3.connect('registro.db')
    # Create cursor (call everytime for any action)
    c = conn.cursor()

    # update submit status and date
    c.execute("UPDATE registro SET submit = ? WHERE oid = (SELECT MAX(oid) FROM registro)",( ticketinfo.get(),) )
    c.execute("UPDATE registro SET submit_date=? WHERE oid = (SELECT MAX(oid) FROM registro)",( time.strftime('%Y/%m/%d %H:%M:%S'),) )
    
    # Commit Changes
    conn.commit()
    # Close Connection
    conn.close()


#querry and display
def query():
    # Create/connect to database
    conn = sqlite3.connect('registro.db')
    # Create cursor (call everytime for any action)
    c = conn.cursor()
    
    #Query the database , use 'oid' for the unique id , Admin can see all entries
    print(accesslevel.get())
    if (accesslevel.get() == 0):
          c.execute("SELECT * FROM registro WHERE cip = ?",(userCIP.get(),))
    else:     
        c.execute("SELECT *,oid FROM registro")
    
    records = c.fetchall()
    #Loop through results
    print_records = ''
    for record in records:
        print_records += str(record) + "\n";
        
    #update query_useinfo
    print("update query")
    query_useinfo.config(state=NORMAL)
    query_useinfo.delete(0.0,END)
    query_useinfo.insert(0.0,print_records)

    if(accesslevel.get() != 0):
        query_useinfo.insert(END, ("kit reserve: " + str(kit_reserve) + " ; Sample stored: " + str(storedsample_count)))
    
    query_useinfo.config(state=DISABLED)
    
    # Commit Changes
    conn.commit()
    # Close Connection
    conn.close()

#delete_all_register
def delete_register():
    # Create/connect to database
    conn = sqlite3.connect('registro.db')
    # Create cursor (call everytime for any action)
    c = conn.cursor()
    
    response = messagebox.askyesno("SALIBANK 1.0","¿Se borrará todo las entradas (menos de los operadores) del registro, continuar?")
    if response == 1:
        #Save DB to backup
        shutil.copy(db_origin,db_backup)        
        #Delete records depending
        if accesslevel == 1:
            c.execute("DELETE FROM registro WHERE CIP != ?", (operatorID));
        else:
            c.execute("DELETE FROM registro");
    # Commit Changes
    conn.commit()
    # Close Connection
    conn.close()
    query() # query again to update.

def copy_register(): #copy db to another location
    shutil.copy(db_origin,db_destination)
    messagebox.showwarning("SALIBANK 1.0","Copia finalizada")

def exit_help():
    raise_frame(f_main)

def restock():
    response = messagebox.askyesno("SALIBANK 1.0","¿Está seguro de rellenar el stock?")
    if response == 1:
        global kit_reserve
        kit_reserve = 200
        messagebox.showwarning("SALIBANK 1.0","Se ha registrado correctamente el cambio")

def empty_storage():
    response = messagebox.askyesno("SALIBANK 1.0","¿Está seguro vaciar el depósito de muestras?")
    if response == 1:
        global storedsample_count
        storedsample_count = 0
        messagebox.showwarning("SALIBANK 1.0","Se ha registrado correctamente el cambio")
    
def display_notification(notification):
    notification_kitdeposited.grid_forget()
    notification_submittip.grid_forget()
    notification_submitsuccess.grid_forget()
    notification_submitfailed.grid_forget()
    notification_printticket.grid_forget()

    
    notification.grid(row=0,column=0,sticky='')
    raise_frame(f_notification)

# ---------------------------- Creating Framework ----------------------------

f_saver = Frame(root)
f_login = Frame(root)
f_language = Frame(root)
f_main = Frame(root)
f_getkit = Frame(root)
f_submit = Frame(root)
f_query = Frame(root)
f_help = Frame(root)
f_notification = Frame(root)

#frames characteristics
for frame in (f_saver, f_login ,f_language, f_main , f_getkit , f_submit, f_query, f_help, f_notification):
    frame.config(bg = "white")
    frame["width"]=screen_width
    frame["height"] = screen_height 
    frame.grid(row=0, column=0, sticky='news')
    frame.grid_propagate(False)

#divide sections for some screens
f_main_head = Frame(f_main)
f_main_body = Frame(f_main)

f_getkit_head = Frame(f_getkit)
f_getkit_body = Frame(f_getkit)

f_submit_head = Frame(f_submit)
f_submit_body = Frame(f_submit)

f_query_head = Frame(f_query)
f_query_body = Frame(f_query)

f_help_head = Frame(f_help)
f_help_body = Frame(f_help)

for frame in (f_main_head, f_getkit_head,f_submit_head,f_query_head,f_help_head):
    frame.config(bg = "bisque")
    frame["width"]= screen_width
    frame["height"] = screen_height/4
    frame.grid(row=0, column=0, sticky='news')
    frame.grid_propagate(False)
    frame.columnconfigure(0,weight=3)
    frame.columnconfigure(1,weight=1)

for frame in (f_main_body, f_getkit_body, f_submit_body, f_query_body,f_help_body):
    frame.config(bg = "white")
    frame["width"]= screen_width
    frame["height"] = screen_height - (screen_height/4)
    frame.grid(row=1, column=0, sticky='news')
    frame.grid_propagate(False)

# ---------------------------- Frames details ----------------------------

# ScreenSaver
# For Raspberry Pi the screen saver is not working and a text (in ssbutton) is used as place holder.
#img = Image.open("screensaver.png")
#photoimg = ImageTk.PhotoImage(img)
ssbutton = Button(f_saver,text = "toque cualquier lugar para continuar" ,command = go_login)
ssbutton.grid(row=0,column=0,sticky="nsew")

f_saver.rowconfigure(0,weight=1)
f_saver.columnconfigure(0,weight=1)

# Login screen
login_title = Label(f_login, text="Bienvenido a SALIBANK", font = ("Verdana", 25))
login_canvas = Canvas(f_login,width=screen_width/4, height= screen_height/3,bg="white",highlightthickness=0)
img = Image.open("TSIdummy.png")
photoimg = ImageTk.PhotoImage(img)
login_canvas.create_image(screen_width/6,0,anchor =NW,image = photoimg)

login_info_message = Label(f_login, text="Pase su tarjeta sanitaria individual por el lector de código de barras",font = ("Verdana",14))
login_entry = Entry(f_login, textvariable = entryvar, borderwidth=0,fg='white', highlightthickness = 0, insertbackground = "white")
login_language = Button(f_login, text="Cambiar Idioma", font = ("Verdana", 12),command=lambda:raise_frame(f_language))
# Bind "Enter" ("<Return>") to funciton. (Barcode Scanners usually use "Return")
root.bind('<Return>',login_return)

login_title.grid(row=0,column=0, columnspan = 2, sticky = "nsew",pady = 10)
login_canvas.grid(row=1,column=0, columnspan = 2, sticky = "nsew",pady = 10)
login_info_message.grid(row=2,column=0, columnspan = 2, sticky = "nsew",pady = 0)
login_entry.grid(row=3,column=0, columnspan = 2, sticky = "nsew",pady = 20)
login_language.grid(row=4,column=1 , sticky = "nsew",padx = 20,pady = 20)
login_entry.focus_set()

f_login.rowconfigure(0,weight=1)
f_login.rowconfigure(1,weight=1)
f_login.rowconfigure(2,weight=1)
f_login.rowconfigure(3,weight=0)
f_login.rowconfigure(4,weight=0)
f_login.columnconfigure(0,weight=1)
f_login.columnconfigure(1,weight=0)

# Change language screen
language_container = Frame(f_language, bg = "white", width = screen_width/3, height = screen_height/3) # Space filler to center buttons
language_spanish = Button(f_language, text= "Castellano",width= 20,height=10,command = go_login) #dummy command, does not actually change language
language_catalan = Button(f_language, text= "Catalán",width= 20,height=10,command = go_login)
language_english = Button(f_language, text= "English",width= 20,height=10,command = go_login)

language_container.grid(row=0,column=0, columnspan = 3, sticky = "nsew",padx = 40)
language_spanish.grid(row=1,column=0, sticky = "nsew",padx = 40)
language_catalan.grid(row=1,column=1, sticky = "nsew",padx = 40)
language_english.grid(row=1,column=2, sticky = "nsew",padx = 40)

f_language.columnconfigure(0,weight=1)
f_language.columnconfigure(1,weight=1)
f_language.columnconfigure(2,weight=1)

# User main screen
main_userdisplay = Label(f_main_head, text = "000",font = ("Verdana", 20))
main_exit = Button(f_main_head, text= "Salir",width= 20,height=5,borderwidth= 4, command = quit_sesion)

main_getkit = Button(f_main_body, text= "Recoger kit", command = go_getkit)
main_submitkit = Button(f_main_body, text= "Enviar muestra",command = go_submit)
main_consult = Button(f_main_body, text= "Consultar",command = go_query)
main_help = Button(f_main_body, text = "Ayuda",command = lambda:raise_frame(f_help))

main_userdisplay.grid(row=0, column=0, sticky="w",padx=30, pady=10)
main_exit.grid(row=0, column=1, sticky="nsew", padx=30, pady=15)

main_getkit.grid(row=1, column=0, rowspan = 2,sticky="nsew", padx=30, pady=20)
main_submitkit.grid(row=1, column=1,rowspan = 2, sticky="nsew", padx=0, pady=20)
main_consult.grid(row=1, column=2, sticky="nsew", padx=30, pady=20)
main_help.grid(row=2, column=2, sticky="nsew", padx=30, pady=20)

f_main_body.rowconfigure(0,weight=2)
f_main_body.rowconfigure(1,weight=5)
f_main_body.rowconfigure(2,weight=5)
f_main_body.columnconfigure(0,weight=3)
f_main_body.columnconfigure(1,weight=3)
f_main_body.columnconfigure(2,weight=2)


# User get kit
getkit_userdisplay = Label(f_getkit_head,text = "0000",font = ("Verdana", 20))
getkit_exit = Button(f_getkit_head, text= "Volver",width= 20,height=5,borderwidth= 4, command = quitgetkit)

getkit_disclaimer = Label(f_getkit_body, text ='''Antes de utiizar el kit:\n
Beber agua 30 minutos antes de la prueba para lavar la cavidad bucal.\n
No se debe ingerir alimento o bebida ni fumar durante los 30 minutos previos a la prueba.\n
Esta prueba deberá realizarse preferiblemente por la mañana.\n
Evitar maquillaje, crema labial o pintalabios que podrían interferir con la prueba.\n
EL USUARIO ES RESPONSABLE DE MANTNER SU MUESTRA LO MAS LIMPIO POSSIBLE''')
getkit_checkbox = Checkbutton(f_getkit_body, text="He leído,entiendo y accepto",onvalue = 1,
                             offvalue = 0,variable = get_kit_enabled,command=enablegetkit)
getkit_accept = Button(f_getkit_body, text= "Reclamar", command = claimkit,state=DISABLED)

getkit_userdisplay.grid(row=0, column=0, sticky="w",padx=30, pady=10)
getkit_exit.grid(row=0, column=1, sticky="nsew", padx=30, pady=15)

getkit_disclaimer.grid(row=0, column=0,sticky="nsew", padx=(20,0), pady=20)
getkit_checkbox.grid(row=1, column=0, sticky="nsew", padx=(20,0), pady=(0,20))
getkit_accept.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=30, pady=20)

f_getkit_body.rowconfigure(0,weight=4)
f_getkit_body.rowconfigure(1,weight=1)
f_getkit_body.columnconfigure(0,weight=2)
f_getkit_body.columnconfigure(1,weight=1)

# User submit sample

submit_userdisplay = Label(f_submit_head,text = "0000",font = ("Verdana", 20))
submit_exit = Button(f_submit_head, text= "Volver",width= 20,height=5,borderwidth= 4,command = lambda:raise_frame(f_main))

submit_sample_guide = Label(f_submit_body,text="""Asegure de que su muestra tenga la pegatina de ID antes de depositarlo\n
Si no lo tiene, puede obtenerlo mediante la opción "Obtener identificador".\n
Puede proceder con la depositación una vez que la muestra tenga el ID pegado.\n
NO SE ACEPTARÁ MUESTRAS SIN IDENTIFICADOR.""")
submit_print_ticket = Button(f_submit_body, text= "Obtener identificador",command = printticket)
submit_sample = Button(f_submit_body, text= "Depositar muestra", command = submitsample)

submit_userdisplay.grid(row=0, column=0, sticky="w",padx=30, pady=10)
submit_exit.grid(row=0, column=1, sticky="nsew", padx=30, pady=15)

submit_sample_guide.grid(row= 0, column= 0, columnspan = 2, sticky = "nsew", padx = 30, pady = 20)
submit_print_ticket.grid(row=1, column=0, sticky="nsew", padx=30, pady=20)
submit_sample.grid(row=1, column=1,sticky="nsew", padx=30, pady=20)

f_submit_body.rowconfigure(0,weight=1)
f_submit_body.rowconfigure(1,weight=2)
f_submit_body.columnconfigure(0,weight=1)
f_submit_body.columnconfigure(1,weight=1)


# Query screen

query_userdisplay = Label(f_query_head,text = "",font = ("Verdana", 20))
query_exit = Button(f_query_head, text= "Volver",width= 20,height=5,borderwidth= 4, command = exit_query)

query_infoheadlines = Label(f_query_body, text = "CIP | Fecha y hora | nº kits solicitados | ID Muestra depositada | Fecha de deposito",font = ("Verdana", 10))
query_useinfo = Text(f_query_body,height = 5)
query_scrollb = Scrollbar(f_query_body,command = query_useinfo.yview)
query_useinfo['yscrollcommand']= query_scrollb.set
query_restock = Button(f_query_body,text="Rellenar kits",command = restock)
query_emptystorage = Button(f_query_body,text="Vaciar muestras",command = empty_storage)
query_copy = Button(f_query_body,text="Duplicar registro",command = copy_register)
query_delete = Button(f_query_body,text="Borrar registro",bg='red',command = delete_register)

query_userdisplay.grid(row=0, column=0, sticky="w",padx=30, pady=10)
query_exit.grid(row=0, column=1, sticky="nsew", padx=30, pady=15)

query_infoheadlines.grid(row = 0, column = 0,columnspan = 4, sticky="news", padx=10, pady=10)
query_useinfo.grid (row = 1, column = 0 ,columnspan = 4, sticky="nsew", padx=(20,0), pady=20 )
query_scrollb.grid(row=1,column=4, sticky="nsew", padx=(0,10), pady=20 )
query_restock.grid(row = 2, column = 0, sticky="news", padx=10, pady=10) #Copy paste to func: login()
query_emptystorage.grid(row = 2, column = 1, sticky="news", padx=10, pady=10) #Copy paste to func: login()
query_copy.grid(row = 2, column = 2, sticky="news", padx=10, pady=10) #Copy paste to func: login()
query_delete.grid(row = 2, column = 3, sticky="news", padx=10, pady=10) #Copy paste to func: login()

f_query_body.rowconfigure(0,weight=1)
f_query_body.rowconfigure(1,weight=3)
f_query_body.rowconfigure(2,weight=1)
f_query_body.columnconfigure(0,weight=12)
f_query_body.columnconfigure(1,weight=12)
f_query_body.columnconfigure(2,weight=12)
f_query_body.columnconfigure(3,weight=12)
f_query_body.columnconfigure(4,weight=1)

# Help screen

help_userdisplay = Label(f_help_head,text = "",font = ("Verdana", 20))
help_exit = Button(f_help_head, text= "Volver",width= 20,height=5,borderwidth= 4,command = exit_help)

help_machineuse = Button(f_help_body, text= "Información general",width= 20)
help_kituse = Button(f_help_body, text= "Uso del kit de saliva",width= 20)
help_submit = Button(f_help_body, text= "Registro de prueba",width= 20)
help_query = Button(f_help_body, text= "Aspectos legales",width= 20)
help_body = Frame(f_help_body, bg = "seashell2")
help_assist = Button(f_help_body, text= "Centro de asistencia",width= 20)

help_userdisplay.grid(row=0, column=0, sticky="w",padx=30, pady=10)
help_exit.grid(row=0, column=1, sticky="nsew", padx=30, pady=15)

help_machineuse.grid(row = 0, column = 0, sticky="news", padx=5, pady=(5,0))
help_kituse.grid(row = 0, column = 1, sticky="news", padx=5, pady=(5,0))
help_submit.grid(row = 0, column = 2, sticky="news", padx=5, pady=(5,0))
help_query.grid(row = 0, column = 3, sticky="news", padx=5, pady=(5,0))
help_body.grid(row = 1, column = 0, columnspan = 4, sticky="news", padx=5, pady=5)
help_assist.grid(row = 2, column = 3, sticky="news", padx=5, pady=5)

f_help_body.rowconfigure(0,weight=1)
f_help_body.rowconfigure(1,weight=5)
f_help_body.rowconfigure(2,weight=1)
f_help_body.columnconfigure(0,weight=1)
f_help_body.columnconfigure(1,weight=1)
f_help_body.columnconfigure(2,weight=1)
f_help_body.columnconfigure(3,weight=1)


# notification screen

notification_kitdeposited = Label(f_notification, text= "Kit depositado, ya puedes recogerlo por la ventana",font = ("Verdana", 10))
notification_submittip = Label(f_notification, text= "Deposite su muestra por la ventana",font = ("Verdana", 10))
notification_submitsuccess = Label(f_notification, text= "Su muestra se ha guardado satisfactoriamente, vovlerá al menú principal en breves momentos",font = ("Verdana", 10),fg = 'green')
notification_submitfailed = Label(f_notification, text= "No se ha detectado ninguna muestra, por favor vuelva a intentar",font = ("Verdana", 10),fg='red')
notification_printticket = Label(f_notification, text= "Se esta imprimiendo el identificador... \nvovlerá automaticamente a la pantalla anterior una vez finalizado",font = ("Verdana", 10))

f_notification.rowconfigure(0,weight=1)
f_notification.columnconfigure(0,weight=1)

# ---------------------------- Fin ----------------------------
raise_frame(f_saver)

root.attributes("-fullscreen", True)
root.mainloop()

