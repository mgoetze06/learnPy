import sys
import json
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout,QHBoxLayout,QPushButton, QComboBox
from PyQt5.QtGui import QPixmap
from PyQt5 import QtWebEngineWidgets
import io

from mapgenerator import generateMap,getFileExtension
from kleinanzeigen import getInformationenFromKleinanzeigenURL


CONST_INI_FILENAME = 'immo.json'
CONST_ALTERNATIVE_INI_FILENAME = 'immos-template.json'


CONST_WINDOW_WIDTH = 1920

class MyApp(QWidget):
    def __init__(self):
        super().__init__()

        # Set the window title
        self.setWindowTitle('immo-saver')

        # Set the window size
        self.resize(CONST_WINDOW_WIDTH, 1080)

        # Create a QLabel to display selected property details
        self.label = QLabel('Select a property from the dropdown:', self)
        self.label.setMaximumSize(CONST_WINDOW_WIDTH, 100)
        # Create a QLabel to display the image
        self.image_label = QLabel(self)
        #self.image_label.setFixedSize(400, 300)  # Set a fixed size for the image display

        # Create a QPushButton
        self.button = QPushButton('Show Details', self)
        self.button.clicked.connect(self.on_button_clicked)

        # Create a QComboBox (Dropdown)
        self.dropdown = QComboBox(self)
        self.load_dropdown_data()  # Load data from JSON file
        self.dropdown.currentTextChanged.connect(self.on_combobox_changed)

        layoutH = QHBoxLayout()
        layoutH.addWidget(self.dropdown)
        layoutH.addWidget(self.button)

        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addLayout(layoutH)
        layout.addWidget(self.image_label)

        m = generateMap()

        data = io.BytesIO()
        m.save(data, close_file=False)
        webengine= QtWebEngineWidgets.QWebEngineView()
        webengine.setHtml(data.getvalue().decode())
        webengine.resize(640, 480)
        layout.addWidget(webengine)

        # Set the layout to the window
        self.setLayout(layout)

    def load_dropdown_data(self):
        """Load data from the JSON file and populate the dropdown with property titles."""
        try:
            with open(CONST_INI_FILENAME, 'r', encoding='utf-8') as file:
                data = json.load(file)
                immos = data.get('immos', [])
                for immo in immos:
                    self.dropdown.addItem(immo['title'], immo)  # Add title to dropdown and store the full object as userData
        except FileNotFoundError:
            print("Error: JSON file not found.")
        except json.JSONDecodeError:
            print("Error: Invalid JSON format.")



    def on_button_clicked(self):
        """Handle button click event to display details and image of the selected property."""
        selected_index = self.dropdown.currentIndex()
        selected_immo = self.dropdown.itemData(selected_index)  # Retrieve the full object associated with the selected title

        if selected_immo:
            # Display property details
            details = (
                f"Title: {selected_immo['title']}\n"
                f"Price: {selected_immo['price']} €\n"
                f"City: {selected_immo['city']}\n"
                f"Address: {selected_immo['address']}\n"
                f"Living Area: {selected_immo['livingarea']} m²\n"
                f"Property Area: {selected_immo['propertyarea']} m²\n"
                f"Construction Year: {selected_immo['constructionyear']}\n"
                f"Description: {selected_immo['description']}\n"
                f"Link: {selected_immo['link']}"
            )
            self.label.setText(details)

            # Load and display the image
            image_path = f"static/images/.jpg"

            filename = f"title_{selected_immo['id']}"
            extension = getFileExtension(filename)
            image_path = "static/images/"+filename+extension
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                #self.image_label.setPixmap(pixmap.scaled(self.image_label.size()))
                self.image_label.setPixmap(pixmap)

            else:
                self.image_label.setText("Image not found.")
        else:
            self.label.setText("No property selected.")
            self.image_label.clear()

    def on_combobox_changed(self):
        self.on_button_clicked()
if __name__ == '__main__':
    # Create the application object
    app = QApplication(sys.argv)


    # Create an instance of your application's main window
    window = MyApp()

    # Show the window
    window.show()

    # Execute the application
    sys.exit(app.exec_())