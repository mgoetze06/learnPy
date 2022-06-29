import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

import ezdxf
import glob
from pathlib import Path
import numpy as np
import sys
from ezdxf import recover
from ezdxf.addons.drawing import matplotlib
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
# Exception handling left out for compactness:

from changeValueDXF import getBlockAttr,updateBlockAttr,exportBlockAttr,checkValidBlock

import os, time
import datetime
import multiprocessing
debug = False

class Revision:
    def __init__(self, bearb, date,text,index):
        self.bearb = bearb
        self.date = date
        self.text = text
        self.index = index
    def print(self):
        print("%s\t%s\t%s\t%s" % (self.index,self.text,self.date,self.bearb))
    def increase(self):
        temp = self.index
        temp = int(temp.replace('R', ''))
        temp += 1
        self.index = "R%d"%(temp)
    def decrease(self):
        temp = self.index
        temp = int(temp.replace('R', ''))
        temp -= 1
        self.index = "R%d"%(temp)
    def create(self):
        print("neue Revision:")
        self.bearb = input("Bearbeiter:")
        self.date = input("Datum:")
        self.index = input("Index (z.b.R1):")
        self.text = input("Text:")
#r1 = Revision("Goe","05/2022","REVISION","R1")
#r2 = Revision(None,None,None,None)
#r2.bearb = "GOE"

#r1.print()
#r1.increase()
#r1.print()
#r2.print()
def query_yes_no(question, default="no"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")

def get_revisionManual(layout,file):
    manualRevision = False
    manualRevs = []
    for i in range(5): #loop through all available layers
        text = 'TEXT[layer=="'+str(i)+'"]'
        texts = layout.query(text)
        if len(texts):
            for t in texts:
                #print(t)
                #print(t.dxf.text)
                if ("REVISION" in t.dxf.text) or ("REV" in t.dxf.text) or ("Hn" in t.dxf.text):
                    #print("manuelle Revision als Text erkannt")
                    manualRevision = True
                    #print(t.dxf.text)
                    temp = t.dxf.text.split(" ")
                    temp_rev = [] #temporary list for the revision info
                    for te in temp:
                        if not te=="":
                            #print(te)
                            if debug:
                                print(te)
                            temp_rev.append(te) #add separated string to temp list
                    if len(temp_rev)>0:
                        if len(temp_rev) > 2:
                            customRevision = Revision(temp_rev[3],temp_rev[2],temp_rev[1],temp_rev[0])
                    #customRevision.print() #create a revision object and print it
                            manualRevs.append(customRevision)
                        else:
                            print("%s\tProblem with REVISION!!!"%file)
    if manualRevision:
        manualRevs.sort(key=lambda x: x.index, reverse=True)
        print("manuelle Revisionen (aus Textfeldern):")
        for rev in manualRevs:
            rev.print()
    return manualRevision

def update_revisionBlock(doc,file,layout,block,revision,position):
    text = 'INSERT[name=="' + block + '"]'
    blockrefs = layout.query(text)
    entity = blockrefs[0]
    revs = ["AEZU", "AETX", "AEDAT", "AENAM"]
    for revtype in revs:
        query = revtype + str(position)
        #value = entity.get_attrib_text(query)
        if "ZU" in revtype:
            entity.get_attrib(query).dxf.text = revision.index
            #print(entity.get_attrib(query).dxf.text)
        if "TX" in revtype:
            entity.get_attrib(query).dxf.text = revision.text
        if "DAT" in revtype:
            entity.get_attrib(query).dxf.text = revision.date
        if "NAM" in revtype:
            entity.get_attrib(query).dxf.text = revision.bearb
        #entity.get_attrib(attr).dxf.text = newText
        if debug:
            print(entity.get_attrib(query).dxf.text)
    doc.saveas(file)
def get_revisionBlock(layout,block):

    text = 'INSERT[name=="' + block + '"]'
    # print(text)
    blockrefs = layout.query(text)
    entity = blockrefs[0]
    revList_inBlock = []
    revs = ["AEZU","AETX","AEDAT","AENAM"]
    free_space_rev_list = [1,2,3] #1 unterste, 2 mittel, 3 oben
    used_space_rev_list = []
    for r in range(4):
        revision = Revision(None,None,None,None)
        count = 0
        for revtype in revs:
            query = revtype + str(r)
            value = entity.get_attrib_text(query)
            if not value=="":
                if "ZU" in revtype:
                    revision.index = value
                    count += 1
                if "TX" in revtype:
                    revision.text = value
                    count += 1
                if "DAT" in revtype:
                    revision.date = value
                    count += 1
                if "NAM" in revtype:
                    revision.bearb = value
                    count += 1
            #Revision(None, None, None, None)

        #only append if every field is filled
        if count > 0:
            revList_inBlock.append(revision)
            used_space_rev_list.append(r) #add used space to list--> track where free space is left

    if debug:
        for obj in revList_inBlock:
            obj.print()
        #for obj in used_space_rev_list:
            #print(obj)
    set_difference = set(free_space_rev_list) - set(used_space_rev_list)
    list_difference = list(set_difference)
    if len(list_difference)>0:
        if debug:
            print("Unterschiede:")
            print(list_difference)
            print("Revision frei an Platz: %d"%np.min(list_difference))
        return np.min(list_difference)
    else:
        if debug:
            print("keine freien Plätze")
        return 0
#blockrefs = layout.query('YA25DE[name=="BEN2"]')
# def exportBlockAttr(doc,layout,block,file,f):
#     text = 'INSERT[name=="'+block+'"]'
#     blockrefs = layout.query(text)
#     if len(blockrefs):
#         entity = blockrefs[0] #process first entity found; only one entity for YA25DE
#         #f = open("blockattr.txt", 'a')
#         temp = "'file';'%s'\n" % (file)
#         f.write(temp)
#         for attrib in entity.attribs:
#             temp = "'%s';'%s'\n" % (attrib.dxf.tag,attrib.dxf.text)
#             f.write(temp)
        #f.close()
# def getBlockAttr(doc,layout,block,attr):
#     #function to display the current data in block attr
#     text = 'INSERT[name=="' + block + '"]'
#     # print(text)
#     blockrefs = layout.query(text)
#     return blockrefs[0].get_attrib(attr).dxf.text
# def updateBlockAttr(doc,layout,block,attr,newText,file):
#     text = 'INSERT[name=="'+block+'"]'
#     #print(text)
#     blockrefs = layout.query(text)
#     if len(blockrefs):
#         entity = blockrefs[0] #process first entity found; only one entity for YA25DE
#         if debug:
#             print("Revisionen vom Block %s:"%(block))
#         #get_revisionBlock(entity)
#         entity.get_attrib(attr).dxf.text = newText
#         pageIndex = entity.get_attrib("ZT").dxf.text
#         if not pageIndex in file:
#                 file = Path(file).stem +"_"+ pageIndex + ".dxf"
#         #for attrib in entity.attribs:
#             #if attrib.dxf.tag == attr: # identify attribute by tag
#             #    attrib.dxf.text = newText # change attribute content to newText
#     doc.saveas(file)
def showPng():
    #file = data
    #print(file)
    #print(name)
    #global file
    #file = glob.glob("*.png")[0]
    #print(file)
    #print("process started")
    last_file_time = "Wed Jun 29 10:51:44 2022"
    i = 0
    while True:
        try:
            #print("trying to get file")
            file = glob.glob("*.png")[0]
            #print(file)

            #doc, auditor = recover.readfile(file)
            #if not auditor.has_errors:
            #    matplotlib.qsave(doc.modelspace(), 'test.png')


        except:
            #print("external sleep")
            time.sleep(1)
            pass
        finally:
            #print("external finally")
            img = mpimg.imread(file)
            # plt.figure(figsize=(10, 10))
            figManager = plt.get_current_fig_manager()

            # monitor = figManager.screenGeometry()
            if debug:
                print(figManager.window)
                print(img.shape)
            # figManager.window.
            figManager.window.move(-1000, 0)
            figManager.window.showMaximized()
            # figManager.window.setFocus()

            h, w, d = img.shape
            img_cropped = img[int(0.75 * h):h, 0:int(0.25 * w), :]  # print only part of the picture
            plt.imshow(img_cropped)
            # plt.draw()
            # plt.show()
            # time.sleep()
            plt.title(file)
            #plt.show(block=False)
            #plt.pause(0.1)
            (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(file)
            file_time = time.ctime(mtime)
            if i == 0:
                last_file_time = file_time
            #print("before while")
            while last_file_time <= file_time:

                # print(str(time.ctime(mtime)))
                try:
                    #print("trying")
                    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(file)
                    file_time = time.ctime(mtime)
                except:
                    #print("breaking")
                    break
                finally:
                    #print("finally")
                    if file_time > last_file_time:
                        #print("file is new")
                        last_file_time = file_time
                        break
                    else:
                        # print("file is old")
                        plt.show(block=False)
                        plt.pause(2)
                        #print("afterpause")
                        # time.sleep(1)
            plt.close()
        i = 1

def exportPNG(file):
    #
    dir_name = os.getcwd()
    test = os.listdir(dir_name)

    for item in test:
        if item.endswith(".png"):
            os.remove(os.path.join(dir_name, item))

    doc, auditor = recover.readfile(file)
    if not auditor.has_errors:
        filename = file + ".png"
        matplotlib.qsave(doc.modelspace(), filename)


if __name__ == '__main__':
    dxffiles = []
    for file in glob.glob("*.dxf"):
        dxffiles.append(file)
    print("###### ------- DXF REVISION CHANGER ------- ######")
    print("Script to change values in %d dxf files (%s ... %s)" % (len(dxffiles),dxffiles[0],dxffiles[-1]))
    blkName = input("Blockname (mostly YA25DE):")
    #attr = input("Attribut (mostly BEN2):")
    #newVal = input("new Value:")
    #blkName = "YA25DE"
    attr = "BEN2"
    if debug:
        print(attr)
        print(blkName)
        #YA25DE #Fußzeile

    f = open("blockattr.txt", 'w+')
    f.write("")
    f.close()
    f = open("blockattr.txt", 'a')
    #print(glob.glob("*.dxf"))

    blocks_to_check = []
    blocks_to_check.append(blkName)
    if blkName == "YA25DE":
        blocks_to_check.append("YA25DE04")
        blocks_to_check.append("YA25DE05")
    if debug:
        print(attr)
        print(blkName)
        print(blocks_to_check)
    new_revision = Revision(None, None, None, None)
    new_revision.create()
    auto_rev = False
    man_rev = True
    no_revs_list = []
    block_dict = {}
    for i,file in enumerate(dxffiles):
        exportPNG(file)
        #print(i)
        #print()
        if i == 0:
            #print("trying to start process")
            p1 = multiprocessing.Process(name='p1', target=showPng, daemon=True)
            p1.start()
        #file = "a0102.dxf"
        doc = ezdxf.readfile(file)
        layout = doc.modelspace()
        blkName = checkValidBlock(doc, layout, attr, blocks_to_check, file)
        if not block_dict.get(blkName):
            block_dict.update({blkName: 1})
        else:
            block_dict.update({blkName: (block_dict.get(blkName) + 1)})
        if debug:
            print(block_dict)
        #print(file)
        print("Datei: %s \t Blatt: %s" % (file,getBlockAttr(doc, layout, blkName, "ZT")))
        #print("Revisionen manuell platzieren")
        #man_rev = get_revisionManual(layout,file)
        #man_rev = not(query_yes_no("Revisionen automatisch platzieren?"))
        if debug:
            print("andere Revisionen gefunden: %s"%man_rev)
        if man_rev:
            #print("Revisionen sind nicht alle im Block %s"%blkName)
            #if(query_yes_no("Revisionen manuell platzieren?")):
            get_revisionManual(layout, file)
            get_revisionBlock(layout, blkName)
            #showPng(file)

            print("Revisionen platzieren an Platz\n(0 to skip; 1 on bottom, 2 middle, 3 top row)")
            place_revs = int(input("Platz:"))
            if (place_revs != 0):
                update_revisionBlock(doc, file, layout, blkName, new_revision, place_revs)
            else:
                no_revs_list.append(file)
        #else:
        if auto_rev:
            free_rev = get_revisionBlock(layout,blkName)
            if free_rev > 0:
                update_revisionBlock(doc,file,layout,blkName,new_revision,free_rev)
            else:
                if debug:
                    print("kein freier Platz für Revision")
                no_revs_list.append(file)
        print("%s\tdone\n" % file)

        exportPNG(file)
        print("Please review file!")
        time.sleep(5)
    f.close()

    print("")
    print("")
    print("###### ----------- Summary ----------- ######")
    print("files:\t\t%d (%s ... %s)" % (len(dxffiles),dxffiles[0],dxffiles[-1]))
    operations = 0
    for x in block_dict.values():
        operations = operations + x
    print("operations:\t%d" % operations)
    print("modified blocks: %s" %block_dict)
    if operations == len(dxffiles):
        print("all files modified")
    else:
        print("error: not all files modified")
    if len(no_revs_list)>0:
        print("!!! Nacharbeit Revisionen: !!!")
        for obj in no_revs_list:
            print(obj)
    #done = input("done")
    p1.terminate()
    p1.join()