#define encoderA 2
#define encoderB 3

volatile int counter = 0; 
volatile int encoderA_state = 0; 
volatile int encoderA_last_state = 0; 
volatile int encoderB_state = 0; 
volatile int encoderB_last_state = 0; 

 void setup() { 
   pinMode (encoderA,INPUT);
   pinMode (encoderB,INPUT);
   //pinMode (button2,INPUT_PULLUP);
   //pinMode (button3,INPUT_PULLUP);
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
   Serial.println(counter);
   delay(20);
 }
void pin_ISR() {
  encoderA_state = digitalRead(encoderA);
  encoderB_state = digitalRead(encoderB);
  if (encoderA_state != encoderA_last_state) {
    // If the encoderB state is different to the encoderA state, that means the encoder is rotating clockwise
    if (encoderB_state != encoderA_state) {
      counter++;
    } else {
      counter--;
    }
    } else {
    if (encoderB_state != encoderB_last_state) {
      // If the encoderB state is different to the encoderA state, that means the encoder is rotating clockwise
      if (encoderA_state != encoderB_state) {
        counter--;
      } else {
        counter++;
      }
    }
  }
  encoderA_last_state = encoderA_state;
  encoderB_last_state = encoderB_state;
}

