from pypdf import PdfReader
import glob
import re

files = glob.glob("./reports/*.pdf")
total_time = 0
total_time_ausfall = 0
einsaetze_total = 0
ausfaelle_total = 0
einsatzzeiten = []
ruhezeiten = []
for file in files:
    print("")
    print("filename: ",file)
    print("")
    reader = PdfReader(file)
    number_of_pages = len(reader.pages)
    ruhezeit = False
    #page = reader.pages[0]
    for page in reader.pages:
        text = page.extract_text()
        #print(text)
        lines = text.split("\n")
        #print(lines)
        indicesOfX = re.finditer(r"Zeiten \(Tasks\)",text)
        indicesOfX = [ind.start() for ind in indicesOfX]

        indicesOfY = re.finditer(r"Ersatzteile",text)
        indicesOfY = [ind.start() for ind in indicesOfY]
        if indicesOfX:
            #print(indicesOfX[0])
            #print(text[indicesOfX[0]:indicesOfX[0]+15])
            if indicesOfY:
                #print(indicesOfY[0])
                #print(text[indicesOfY[0]:indicesOfY[0]+15])

                #print("")
                einsaetze = text[indicesOfX[0]:indicesOfY[0]]
                if "Ruhezeit" in einsaetze:
                    ruhezeit = True
                einsaetze = einsaetze.split("\n")
                #print(einsaetze)
                for line in einsaetze:
                    split_line = line.split(" ")
                    split_line = [x for x in split_line if x != ""]

                    if len(split_line) > 3:
                        if "()" in line or ")" in line:
                            #skip
                            #print("skipping line")
                            thisnot = ""
                        else:
                            print(split_line)
                            startdate = split_line[0] + " " + split_line[1] 
                            enddate = split_line[2] + " " + split_line[3] 
                            time = split_line[4].strip().replace(",",".")
                            try:
                                if ruhezeit:
                                    total_time_ausfall = total_time_ausfall + float(time)
                                    ruhezeiten.append(float(time))
                                    print("addiere Ruhezeit: ",total_time_ausfall)
                                    ausfaelle_total += 1

                                else:
                                    total_time = total_time + float(time)
                                    print("addiere Arbeitszeit: ",total_time)
                                    einsaetze_total += 1
                                    einsatzzeiten.append(float(time))


                            except:
                                print("time parsing fehlgeschlagen",time)

                            print("Von ",startdate, " bis ",enddate," Insgesamt: ",time, "h")
print("Einsätze enthalten", total_time, " h Arbeitszeit")
print("Einsätze enthalten", total_time_ausfall, " h Ruhezeit")
print("Einsätze: " ,einsaetze_total)
print("maximale Ruhezeit: ",max(ruhezeiten))
print("minimale Ruhezeit: ",min(ruhezeiten))
print("maximale Arbeitszeit: ",max(einsatzzeiten))
print("minimale Arbeitszeit: ",min(einsatzzeiten))
print("durchschnittliche Arbeitszeit:", total_time/len(einsatzzeiten))
print("durchschnittliche Ausfallzeit:", total_time_ausfall/len(ruhezeiten))