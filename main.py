from tkinter import *
import random


colours = [
    'Red', 'Blue', 'Green', 'Pink', 'Black', 'Yellow', 'Orange', 'White',
    'Purple', 'Brown'
]

score = 0


time_left = 30


def menu():
    mainmenu = Menu(root) 
    root.config(menu=mainmenu)
    filemenu = Menu(mainmenu, tearoff=0)
    filemenu.add_command(label="Open", font=("Times New Roman", 16,"bold"), foreground="gray", background="lightblue")
    filemenu.add_command(label="New", font=("Times New Roman", 16,"bold"), foreground="gray", background="lightblue")
    filemenu.add_command(label="Save", font=("Times New Roman", 16,"bold"), foreground="gray", background="lightblue")
    filemenu.add_separator()
    filemenu.add_command(label="Exit", font=("Times New Roman", 16,"bold"), foreground="red", background="limegreen")
    
    helpmenu = Menu(mainmenu, tearoff=0)
    helpmenu.add_command(label="Help", font=("Times New Roman", 16,"bold"))
    helpmenu.add_command(label="About", font=("Times New Roman", 16,"bold"))
    
    mainmenu.add_cascade(label="Menu",
                        menu=filemenu, font=("Times New Roman", 20,"bold"))
    mainmenu.add_cascade(label="Spravka",
                        menu=helpmenu,font=("Times New Roman", 20,"bold"))

def score_out():
    global score, time_left
    end = Label(root,
    text="Your score: "+ str(score),
    font=("Times New Roman", 20))
    end.pack()


    score = 0
    time_left = 30


def start_game(event):
    if time_left == 30:
        count_down()
    next_colour()


def next_colour():
    global score
    global time_left

    e.focus_set()
    if e.get().lower() == colours[1].lower():
        score += 1
    e.delete(0, tkinter.END)

    random.shuffle(colours)

    label.config(fg=str(colours[1]), text=str(colours[0]))

    scoreLabel.config(text="Score: " + str(score))


def count_down():
    global time_left
    if time_left > 0:

        time_left -= 1

        timeLabel.config(text="Time Left: " + str(time_left))

        timeLabel.after(1000, count_down)
    else:
        score_out()


root = Tk()

root.title("COLORGAME")

root.geometry("700x500")

menu()

instructions = Label(
    root,
    text="""Type in the colour of the words,
                                        \n and not in the word text """,
    font=("Times New Roman", 20))
instructions.pack()

scoreLabel = Label(
    root, text="Press enter to start", font=("Times New Roman", 32))
scoreLabel.pack()

timeLabel = Label(
    root, text="TimeLeft: " + str(time_left), font=("Times New Roman", 32))
timeLabel.pack()



label = Label(root, font=("Times New Roman", 32))
label.pack()

e = Entry(root, font=("Times New Roman", 20), bd=8)

root.bind('<Return>', start_game)
e.pack()

e.focus_set()

root.mainloop()
