#define encoderA 12
#define encoderB 13
#define button2 2
#define button3 3
//#define button4 4

 int counter = 0; 
 int aState;
 bool b2;
 //bool b3;
 //bool b4;
 int aLastState;  
 volatile int buttonState = 0; 

 void setup() { 
   pinMode (encoderA,INPUT);
   pinMode (encoderB,INPUT);
   pinMode (button2,INPUT_PULLUP);
   pinMode (button3,INPUT_PULLUP);
   //pinMode (button4,INPUT_PULLUP);
   
   Serial.begin (115200);
   // Reads the initial state of the encoderA
   aLastState = digitalRead(encoderA);   
   attachInterrupt(0, pin_ISR, FALLING);
   attachInterrupt(1, pin_ISR_1, FALLING);
 } 

 void loop() { 
   aState = digitalRead(encoderA);
   b2 = digitalRead(button2);
   //b3 = digitalRead(button3);
   //b4 = digitalRead(button4);   // Reads the "current" state of the encoderA
   // If the previous and the current state of the encoderA are different, that means a Pulse has occured
   if (aState != aLastState){     
     // If the encoderB state is different to the encoderA state, that means the encoder is rotating clockwise
     if (digitalRead(encoderB) != aState) { 
       counter ++;
     } else {
       counter --;
     }
    Serial.print("P");
    Serial.print(counter);
    Serial.print("BA");
    Serial.print("0");
    Serial.print("BB");
    Serial.println("0");

   } 
   aLastState = aState; // Updates the previous state of the encoderA with the current state
   
 }
void pin_ISR() {
  //buttonState = digitalRead(button2);
  //digitalWrite(ledPin, buttonState);
  Serial.print("P");
  Serial.print(counter);
  Serial.print("BA");
  Serial.print("1");
  Serial.print("BB");
  Serial.println("0");
}

void pin_ISR_1() {
  //buttonState = digitalRead(button2);
  //digitalWrite(ledPin, buttonState);
  Serial.print("P");
  Serial.print(counter);
  Serial.print("BA");
  Serial.print("0");
  Serial.print("BB");
  Serial.println("1");
}
