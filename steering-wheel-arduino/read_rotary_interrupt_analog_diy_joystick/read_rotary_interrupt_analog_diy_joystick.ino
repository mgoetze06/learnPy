#define encoderA 2
#define encoderB 3
#define trigger1_pin 4
#define trigger2_pin 5
#define trigger3_pin 6
#define trigger4_pin 7

volatile int counter = 0; 
volatile int last_counter = 0; 
volatile int encoderA_state = 0; 
volatile int encoderA_last_state = 0; 
volatile int encoderB_state = 0; 
volatile int encoderB_last_state = 0; 
int zero_detection = 0;

int sensorPin = A0;
int sensorPin2 = A1;   // select the input pin for the potentiometer
//int ledPin = 13;      // select the pin for the LED
int sensorValue = 0;
int sensorValue2 = 0;
int trigger1 = 0;
int trigger2 = 0;
int trigger3 = 0;
int trigger4 = 0;

 void setup() { 
   pinMode (encoderA,INPUT);
   pinMode (encoderB,INPUT);
   pinMode (trigger1_pin,INPUT_PULLUP);
   pinMode (trigger2_pin,INPUT_PULLUP);
   pinMode (trigger3_pin,INPUT_PULLUP);
   pinMode (trigger4_pin,INPUT_PULLUP);
   //pinMode (button4,INPUT_PULLUP);
   
   Serial.begin (115200);
   // Reads the initial state of the encoderA
   //aLastState = digitalRead(encoderA);   
   attachInterrupt(0, pin_ISR, CHANGE);
   attachInterrupt(1, pin_ISR, CHANGE);
 } 

 void loop() { 
   if(counter > 3000){
      counter = 3000;
   }else{
     if (counter < -3000){
       counter = -3000;
     }
   }
   if (last_counter == counter){
     zero_detection++;
   }
  if ((zero_detection > 200) && (counter < 315) && (counter > -315)){
     zero_detection = 0;
     counter = 0;
     last_counter = 0;
   }
    sensorValue = analogRead(sensorPin);
    Serial.print("S1:");
    Serial.print(sensorValue);
    Serial.print("S2:");
    sensorValue2 = analogRead(sensorPin2);
    Serial.print(sensorValue2);
    Serial.print("S3:");
    Serial.print(counter);
    trigger1 = digitalRead(trigger1_pin);
    Serial.print("S4:");
    Serial.print(trigger1);
    trigger2 = digitalRead(trigger2_pin);
    Serial.print("S5:");
    Serial.print(trigger2);
    trigger3 = digitalRead(trigger3_pin);
    Serial.print("S6:");
    Serial.print(trigger3);
    trigger4 = digitalRead(trigger4_pin);
    Serial.print("S7:");
    Serial.println(trigger4);
    delay(8);
 }
void pin_ISR() {
  encoderA_state = digitalRead(encoderA);
  encoderB_state = digitalRead(encoderB);
  if (encoderA_state != encoderA_last_state) {
    // If the encoderB state is different to the encoderA state, that means the encoder is rotating clockwise
    if (encoderB_state != encoderA_state) {
      addCounter();
    } else {
      decCounter();
    }
    } else {
    if (encoderB_state != encoderB_last_state) {
      // If the encoderB state is different to the encoderA state, that means the encoder is rotating clockwise
      if (encoderA_state != encoderB_state) {
        decCounter();
      } else {
        addCounter();
      }
    }
  }
  encoderA_last_state = encoderA_state;
  encoderB_last_state = encoderB_state;
  last_counter = counter;
}
void addCounter(){
  //if ((last_counter == 0) && (zero_counter > 30)){

  //}
  if ((counter < 300) && (counter > -300)){
    counter = 300;
  }else{
    counter++;
  }
}
void decCounter(){
  if ((counter < 300) && (counter > -300)){
    counter = -300;
  }else{
    counter--;
  }
  
}

