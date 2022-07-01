import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

import ezdxf
import glob
from ezdxf import groupby
from pathlib import Path

debug = False
onlyExport = False

def exportBlockAttr(dxffiles):
    for file in dxffiles:
        csv_str = "'%s';" % file
        print(file)
        doc = ezdxf.readfile(file)
        layout = doc.modelspace()
        group = layout.groupby(dxfattrib="layer")
        print(group.items())
        for layer, entities in group.items():
            #print(f'Layer "{layer}" contains following entities:')
            for entity in entities:
                #print(f"    {entity}")
                #print(entity.__str__())
                #print(entity.dxftype())
                if entity.dxftype() == 'TEXT':
                    print(entity.dxf.text)
                    #print(entity.dxf.tag)
                    pos = entity.get_pos()
                    print(pos)
                    print(pos[0])
                    print(pos[1])
                        #print(entity.text)
                    #print("all existing:")
                    #print(entity.all_existing_dxf_attribs())
                    #for attr in entity.all_existing_dxf_attribs():
                    #    print(attr)

            print("-" * 40)
        #text = 'INSERT[name=="'+block+'"]'
        #blockrefs = layout.query(text)
        blockrefs = layout.query('*')
        print(blockrefs)
        for entity in blockrefs:
            #f = open("blockattr.txt", 'a')
            #temp = "'file';'%s'\n" % (file)
            #f.write(temp)
            #print(entity.__str__())
            #print(entity.dxftype())
            #print(entity.dxf.Name)
            #print(entity['name'])
            try:
                if entity.dxf_attrib_exists:
                    temp = ""
                    for attrib in entity.attribs:
                        if not attrib.dxf.text == '':
                            temp = temp + "'%s';'%s';" % (attrib.dxf.tag,attrib.dxf.text)
                    print(temp)
                    #f.close()
            except:
                pass
        for insert in layout.query('INSERT'):
            block = doc.blocks[insert.dxf.name]
           # print(insert.dxf.name)
            temp = "'" + insert.dxf.name + "';"
            for e in insert.attribs:
                try:
                    #if not e.dxf.text == "":
                     temp = temp + "'%s';'%s';" % (e.dxf.tag, e.dxf.text)

                except:
                    pass
            print(temp)
def getBlockAttr(doc,layout,block,attr):
    #function to display the current data in block attr
    text = 'INSERT[name=="' + block + '"]'
    # print(text)
    blockrefs = layout.query(text)
    #print(blockrefs)
    #print(blockrefs[0].get_attrib(attr).dxf.text)
    text = None
    try:
        #print("searching for block")
        text = blockrefs[0].get_attrib(attr).dxf.text
        #print(text)
    except:
        pass
    return text
def updateBlockAttr(doc,layout,block,attr,newText,file):
    text = 'INSERT[name=="'+block+'"]'
    #print(text)
    blockrefs = layout.query(text)
    if len(blockrefs):
        entity = blockrefs[0] #process first entity found; only one entity for YA25DE
        oldtext = entity.get_attrib(attr).dxf.text
        entity.get_attrib(attr).dxf.text = newText
        pageIndex = entity.get_attrib("ZT").dxf.text
        if debug:
            print("changed from %s to %s"%(oldtext,newText))

        #if not pageIndex in file:
                #file = Path(file).stem +"_"+ pageIndex + ".dxf"
        #for attrib in entity.attribs:
            #if attrib.dxf.tag == attr: # identify attribute by tag
            #    attrib.dxf.text = newText # change attribute content to newText
    doc.saveas(file)


def checkValidBlock(doc,layout,attr,blocks_to_check,file):
    valid_block = None
    local_block_list = blocks_to_check
    for blk in local_block_list:
        if getBlockAttr(doc, layout, blk, attr) == None:
            # blk does not exist
            if debug:
                print(blk)
                print("this is the value: ")
                print(getBlockAttr(doc, layout, blk, attr))
                print("%s\tblock %s not found" % (file, blk))
            local_block_list.remove(blk)
        else:
            # blk does exist
            valid_block = blk
            break

    if not valid_block:
        valid_block = local_block_list[0]
    if debug:
        print("local blocks: %s" % local_block_list)
        print(local_block_list)
        print(valid_block)

    return valid_block

def changeValue(dxffiles):

    print("###### ------- DXF VALUE CHANGER ------- ######")
    print("Script to change values in %d dxf files (%s ... %s)" % (len(dxffiles),dxffiles[0],dxffiles[-1])) #show summary of files
    blkName = input("Blockname (mostly YA25DE):")
    attr = input("Attribut (mostly BEN2):")
    newVal = input("new Value:")
    #blkName = "YA25DE"
    #attr = "BEN2"
    #newVal = "test"


        #YA25DE #Fußzeile
    blocks_to_check = []
    blocks_to_check.append(blkName)
    if blkName == "YA25DE":
        blocks_to_check.append("YA25DE04")
        blocks_to_check.append("YA25DE05")
    if debug:
        print(attr)
        print(blkName)
        print(blocks_to_check)
    #f = open("blockattr.txt", 'w')
    f = open('blockattr.txt', 'w+')#create a blockattr file that stores all attributes of the selected block and their value
    #print(glob.glob("*.dxf"))

    block_dict = {}

    for file in dxffiles:
        print(file, end="\r")
        #file = "a0102.dxf"
        doc = ezdxf.readfile(file)
        layout = doc.modelspace()
        if debug:
            print("value before change: %s" % getBlockAttr(doc,layout,blkName,attr))
        valid_block = checkValidBlock(doc,layout,attr,blocks_to_check,file)

        if not block_dict.get(valid_block):
            block_dict.update({valid_block: 1})
        else:
            block_dict.update({valid_block: (block_dict.get(valid_block)+1)})
        if debug:
            print(block_dict)

        updateBlockAttr(doc,layout,valid_block,attr,newVal,file)
        if debug:
            print("value after change: %s" % getBlockAttr(doc,layout,valid_block,attr))


        exportBlockAttr(doc,layout,valid_block,file,f)
        print("%s\t\t\tdone" % file)
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
    input("done")
if __name__ == "__main__":
    dxffiles = []
    for file in glob.glob("*.dxf"):
        #get all dxf files from current directory
        dxffiles.append(file)
    if onlyExport:
        exportBlockAttr(dxffiles)
    else:
        changeValue(dxffiles)