import nbformat
import glob, os

files = []
extension = ".ipynb"

for file in glob.glob("*" + extension):
    files.append(file)
files.sort(key=os.path.getmtime)    #[0] oldest
                                    #[-1] newest
print(files)

mergefile = input("Welche Datei am Ende überschrieben werden? (Name oder Index): ")
try:
    num = int(mergefile)
    print(num)
    mergefile = files[num]
except ValueError:
    print('The provided value is not a number')
if mergefile.endswith(extension):
    print("file ends with " + extension)
else:
    mergefile = mergefile + extension
isExist = os.path.exists(mergefile)
print(isExist)
if isExist:
    c = input(mergefile + " ist vorhanden und wird überschrieben [y/n]: ")
    if c == "y":
        print("user bestätigt")
    else:
        exit(0)
else:
    #new notebook
    print("neues notebook")

for i in range(len(files)):
    print(files[i])
    nb = nbformat.read(files[i], 4)
    if i == 0:
        final_notebook = nbformat.v4.new_notebook(metadata=nb.metadata)
    final_notebook.cells = final_notebook.cells + nb.cells
    print(files[i] + " wurde geladen.")
nbformat.write(final_notebook, mergefile)
print(mergefile + " wurde gespeichert.")
# Reading the notebooks
#first_notebook = nbformat.read('1.ipynb', 4)
#second_notebook = nbformat.read('2.ipynb', 4)

# Creating a new notebook
#final_notebook = nbformat.v4.new_notebook(metadata=first_notebook.metadata)

# Concatenating the notebooks
#final_notebook.cells = first_notebook.cells + second_notebook.cells

# Saving the new notebook 
#nbformat.write(final_notebook, 'combined.ipynb')
