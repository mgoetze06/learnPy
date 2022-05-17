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

r1 = Revision("Goe","05/2022","REVISION","R1")
r2 = Revision(None,None,None,None)
r2.bearb = "GOE"

r1.print()
r1.increase()
r1.print()
r2.print()
def get_revision(attributes):
    print(" ")

def set_revision(entity):
    revList = []
    revs = ["AEZU","AETX","AEDAT","AENAM"]
    for r in range(3):
        revision = Revision(None,None,None,None)
        for revtype in revs:
            query = revtype + str(r)
            value = entity.get_attrib_text(query)
            if not value=="":
                if "ZU" in revtype:
                    revision.index = value
                if "TX" in revtype:
                    revision.text = value
                if "DAT" in revtype:
                    revision.date = value
                if "NAM" in revtype:
                    revision.bearb = value
            #Revision(None, None, None, None)
        revList.append(revision)
    for obj in revList:
        obj.print()
def print_revision(attributes):
    print(" ")
dxffiles = []
for file in glob.glob("*.dxf"):
    dxffiles.append(file)
print("Script Changing values in %d dxf files (%s ... %s)" % (len(dxffiles),dxffiles[0],dxffiles[-1]))
#blkName = input("Blockname:")
blkName = "YA25DE"
print(blkName)
    #YA25DE #Fußzeile

#print(glob.glob("*.dxf"))
for file in dxffiles:

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

    #blockrefs = layout.query('YA25DE[name=="BEN2"]')
    text = 'INSERT[name=="'+blkName+'"]'
    #print(text)
    blockrefs = layout.query(text)
    texts = layout.query('TEXT[layer=="1"]')
    for t in texts:
        print(t)
        print(t.dxf.text)
    print(texts[0].dxf.text)
    #print(texts[0].dxf.tag)
    #blockrefs = layout.query('INSERT[name=="YA25DE"]')
    #print(blockrefs)
    if len(blockrefs):
        entity = blockrefs[0] # process first entity found
        #print(entity.dxf.name)
        set_revision(entity)
        #query="AEZU1"
        #print(entity.get_attrib_text(query))
        for attrib in entity.attribs:
            #print(attrib)
            #print(attrib.dxf.tag)
            #print(attrib.dxf.text)
            if attrib.dxf.tag == "BEN2": # identify attribute by tag
                #print(attrib.dxf.text)
                attrib.dxf.text = "DAS IST EIN TEST" # change attribute content
                #print(attrib.dxf.text)
            if attrib.dxf.tag == "ZT": #Blattnummer wird mit an den Dateinamen angehangen
                if not attrib.dxf.text in file:
                    file = Path(file).stem +"_"+ attrib.dxf.text + ".dxf"
                    #print(file)
    doc.saveas(file)
#page_setup(size=(297, 210), margins=(10, 15, 10, 15), units='mm', offset=(0, 0), rotation=0, scale=16, name='ezdxf', device='DWG to PDF.pc3')