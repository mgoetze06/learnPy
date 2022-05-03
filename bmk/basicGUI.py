import tkinter as tk

window = tk.Tk()
window.title("BMK Erstellung")
window.geometry("600x700") #general size
window.resizable(width=False, height=False)

masterframe = tk.Frame(master=window)
masterframe.grid(row=0, column=0,sticky="ne")
masterframe.columnconfigure([0,1,2,3,4,5], minsize=50)
masterframe.rowconfigure([0, 1, 2, 3], minsize=30)

frame_00 = tk.Frame(master=masterframe)
frame_00.grid(row=0, column=0,sticky="ne")
frame_10 = tk.Frame(master=masterframe)
frame_10.grid(row=1, column=0,sticky="n")
frame_01 = tk.Frame(master=masterframe)
frame_01.grid(row=0, column=1,sticky="e")
frame_12 = tk.Frame(master=masterframe)
frame_12.grid(row=1, column=2,sticky="e")
frame_21 = tk.Frame(master=masterframe)
frame_21.grid(row=2, column=1,sticky="e")

entry_01 = tk.Entry(master=frame_01, width=5)
label_01 = tk.Label(master=frame_01, text="Grid01", bg="grey")
entry_01.grid(row=0,column=0,sticky="ne")
label_01.grid(row=0,column=1,sticky="ne")

entry_10 = tk.Entry(master=frame_10, width=5)
label_10 = tk.Label(master=frame_10, text="Grid10", bg="grey")
entry_10.grid(row=0,column=0,sticky="ne")
label_10.grid(row=0,column=1,sticky="ne")

entry_12 = tk.Entry(master=frame_12, width=5)
label_12 = tk.Label(master=frame_12, text="Grid12", bg="grey")
entry_12.grid(row=0,column=0,sticky="ne")
label_12.grid(row=0,column=1,sticky="ne")

entry_21 = tk.Entry(master=frame_21, width=5)
label_21 = tk.Label(master=frame_21, text="Grid22", bg="grey")
entry_21.grid(row=0,column=0,sticky="ne")
label_21.grid(row=0,column=1,sticky="ne")

label2 = tk.Label(master=window,text="Hier könnte ihre Werbung stehen")
label2.grid(row=1,column=0,sticky="nsew")


def handleUserInput(input):

    return input

def handle_click(event):
    print("The button was clicked!")
    value1 = handleUserInput(entry_01.get())
    value2 = handleUserInput(entry_10.get())
    value3 = handleUserInput(entry_12.get())
    value4 = handleUserInput(entry_21.get())
    print(value1)
    print(value2)
    print(value3)
    print(value4)
button = tk.Button(text="Click me!",master=window)
button.grid(row=2,column=0,sticky="nsew")
button.bind("<Button-1>", handle_click)

def handle_increaser(event):
    value = int(label_increaser["text"])
    label_increaser["text"] = f"{value + 1}"
    placeLabel()
    return
def handle_decreaser(event):
    value = int(label_increaser["text"])
    label_increaser["text"] = f"{value - 1}"
    placeLabel()
    return
increaserframe = tk.Frame(master=window)
increaserframe.grid(row=3, column=0,sticky="e")
increaserframe.columnconfigure([0,1,2], minsize=60)
increaserframe.rowconfigure(0, minsize=40)

button = tk.Button(text="+",master=increaserframe)
button.grid(row=0,column=0,sticky="nsew")
button.bind("<Button-1>", handle_increaser)

button = tk.Button(text="-",master=increaserframe)
button.grid(row=0,column=2,sticky="nsew")
button.bind("<Button-1>", handle_decreaser)

label_increaser = tk.Label(master=increaserframe,text="0")
label_increaser.grid(row=0,column=1,sticky="nsew")

label_absolute = tk.Label(master=window, text="I'm at (75, 75)", bg="yellow")

label_paper = tk.Label(master=window, text="A4", bg="green")
label_paper.place(x=380, y=10, width=200,height=350)

label_paper_top = tk.Label(master=window, text="top", bg="grey")
label_paper_top.place(x=460, y=10,height=10, width=50)

label_paper_bot = tk.Label(master=window, text="bot", bg="grey")
label_paper_bot.place(x=460, y=350, width=50,height=10)
def placeLabel():
    xcoord = int(label_increaser["text"]) * 10
    print(xcoord)
    label_absolute["text"] = f"I'm at ({xcoord}, 75)"
    label_absolute.place(x=xcoord, y=75)

#number_entry.grid(row=0,column=0,sticky="nsew")
#label_entry.grid(row=0,column=1)

#greeting = tk.Label(window,text="Hello, Tkinter")
#greeting.pack()
#frame_entry.place()
#label_1=tk.Label(master=window, text="Text", bg="black")
#label_1.grid(row=1, column=0,sticky="nsew")


window.mainloop()
