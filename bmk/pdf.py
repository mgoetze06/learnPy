from fpdf import FPDF  # fpdf class

class PDF(FPDF):
    pass #nothing

pdf_w=210
pdf_h=297
font_h=3.25     #needs to be fine tuned based on font

d_top = 5       #distance from top of paper to first element
d_left = 5      #distance from left of paper to first element
e_width = 15    #width of bmk sticking element
e_height = 5    #height of bmk sticking element
d_e_x = 5       #distance between bmk elements horirzontally
d_e_y = 5       #distance between bmk elements vertically
desired_text_height = 8 #absolute text height in mm --> text is placed centered in bmk element

with open("bmk_short.txt", "r", encoding='utf8') as f:
    lines = f.readlines()
    lines = [line.rstrip() for line in lines]
f.close()
print(lines)
print(len(lines))
pdf = PDF() #pdf object
pdf = PDF(orientation='P', unit='mm', format='A4')
pdf.set_margins(left=0, top=0, right=0)
pdf.add_page()
pdf.set_font('Arial', '', 12) #B for bold, empty for regular
pdf.set_line_width(0.0)
pdf.line(0,0,pdf_w/2,pdf_h/2)
pdf.set_xy(0.0,0.0)
pdf.text(0, font_h, 'Startup')
for i in range(len(lines)):
    #pdf.set_xy(0,i*20)
    pdf.text(0, (i*20)+2*font_h, lines[i])
    string_w = pdf.get_string_width(lines[i])
    print(string_w)
    pdf.line(0,(i*20)+2*font_h,string_w,(i*20)+2*font_h)











pdf.output('test.pdf','F')