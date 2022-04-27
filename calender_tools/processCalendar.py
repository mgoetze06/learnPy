import csv


def openCsv(filename):
    with open(filename)as csvfile:

        filereader = csv.DictReader(csvfile, delimiter=",")
        data = list(filereader)
        #filereader = csv.reader(csvfile, delimiter=",")
        #for row in filereader:
            #print(row)
            #print("Subject:",row['olApt.Subject'],"\nvon: ",row['olApt.Start'], " bis ", row['olApt.End'], "\nOrt: ",row['olApt.Location'])
        return data

my_csv = openCsv("outlook.csv")
#print(my_csv)
for row in my_csv:
    #for item in row:
     #   print(item)
    # print(row)
    print(row['olApt.Subject'])