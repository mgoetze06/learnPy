import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

import ezdxf
import glob
from pathlib import Path

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

#r1 = Revision("Goe","05/2022","REVISION","R1")
#r2 = Revision(None,None,None,None)
#r2.bearb = "GOE"

#r1.print()
#r1.increase()
#r1.print()
#r2.print()

def get_revisionManual(layout):
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
                            temp_rev.append(te) #add separated string to temp list
                    customRevision = Revision(temp_rev[3],temp_rev[2],temp_rev[1],temp_rev[0])
                    #customRevision.print() #create a revision object and print it
                    manualRevs.append(customRevision)
    if manualRevision:
        print("manuelle Revisionen (aus Textfeldern):")
        manualRevs.sort(key=lambda x: x.index, reverse=True)
        for rev in manualRevs:
            rev.print()

def get_revisionBlock(entity):
    revList_inBlock = []
    revs = ["AEZU","AETX","AEDAT","AENAM"]
    for r in range(3):
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
    for obj in revList_inBlock:
        obj.print()

#blockrefs = layout.query('YA25DE[name=="BEN2"]')
def getBlockAttr(doc,layout,block,attr):
    text = 'INSERT[name=="' + block + '"]'
    # print(text)
    blockrefs = layout.query(text)
    return blockrefs[0].get_attrib(attr).dxf.text
def updateBlockAttr(doc,layout,block,attr,newText,file):
    text = 'INSERT[name=="'+block+'"]'
    #print(text)
    blockrefs = layout.query(text)
    if len(blockrefs):
        entity = blockrefs[0] #process first entity found; only one entity for YA25DE
        print("Revisionen vom Block %s:"%(block))
        get_revisionBlock(entity)
        entity.get_attrib(attr).dxf.text = newText
        pageIndex = entity.get_attrib("ZT").dxf.text
        if not pageIndex in file:
                file = Path(file).stem +"_"+ pageIndex + ".dxf"
        #for attrib in entity.attribs:
            #if attrib.dxf.tag == attr: # identify attribute by tag
            #    attrib.dxf.text = newText # change attribute content to newText
    doc.saveas(file)

dxffiles = []
for file in glob.glob("*.dxf"):
    dxffiles.append(file)
print("Script Changing values in %d dxf files (%s ... %s)" % (len(dxffiles),dxffiles[0],dxffiles[-1]))
#blkName = input("Blockname:")
blkName = "YA25DE"
print(blkName)
    #YA25DE #Fußzeile

#print(glob.glob("*.dxf"))
#for file in dxffiles:
file = "a0102.dxf"
doc = ezdxf.readfile(file)
layout = doc.modelspace()
#blk = doc.blocks.get("YA25DE")#.get_attrib('BEN2')
#print(blk.dxf.dxfattribs.get_attrib('BEN2'))
#for attrib in blk.dxf.dxfattribs:
#    print(attrib.tag)
#print(blk.dxf.dxfattribs)
#print(blk)
#print(doc.layout_names())
#psp = doc.layout('Layout1')
get_revisionManual(layout)
print(getBlockAttr(doc,layout,blkName,"BEN2"))
updateBlockAttr(doc,layout,blkName,"BEN2","DAS IST EIN ZWEITER TEST",file)
print(getBlockAttr(doc,layout,blkName,"BEN2"))
