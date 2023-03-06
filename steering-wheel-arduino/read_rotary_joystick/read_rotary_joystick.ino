// Simple arcade stick example that demonstrates how to read twelve
// Arduino Pro Micro digital pins and map them to the
// Arduino Joystick library.
//

// The digital pins 2 - 20 are grounded when they are pressed.
// Pin 10, A10, Red = UP
// Pin 15, D15, Yellow = RIGHT
// Pin 16, D16, Orange = DOWN
// Pin 14, D14, Green = LEFT

// Pin 9, A9 = Button 1
// Pin 8, A8 = Button 2
// Pin 7, D7 = Button 3
// Pin 3, D3 = Button 4
// Pin 2, D2 = Button 5
// Pin 4, A6 = Button 6

// Pin 20, A2 = Select Button 1
// Pin 19, A1 = Start Button 2

// Pin 5, D5 = Other Button
// Pin 6, A7 = Other Button
// Pin 18, A0 = Other Button
// Pin 21, A3 = Other Button

// NOTE: This sketch file is for use with Arduino Pro Micro only.
//
// Original gamepad example by Matthew Heironimus
// 2016-11-24
// Adapted for arcade machine setup by Ben Parmeter
// 2019-05-20
//--------------------------------------------------------------------
#include <Joystick.h>
#define encoderA 2
#define encoderB 3

volatile int counter = 0; 
volatile int encoderA_state = 0; 
volatile int encoderA_last_state = 0; 
volatile int encoderB_state = 0; 
volatile int encoderB_last_state = 0; 


Joystick_ Joystick(JOYSTICK_DEFAULT_REPORT_ID,JOYSTICK_TYPE_GAMEPAD,
  0, 0,                  // Button Count, Hat Switch Count
  fals, false, false,     // X and Y, but no Z Axis
  false, false, false,   // No Rx, Ry, or Rz
  false, false,          // No rudder or throttle
  false, false, true);  // No accelerator, brake, or steering

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
  // Initialize Joystick Library
  Joystick.begin();
  Joystick.setSteeringRange(-3000, 3000);
}



void loop() {
  if(counter > 3000){
    counter = 3000;
  }else{
    if (counter < -3000){
      counter = -3000;
    }
  }
  Joystick.setSteering(counter);
  delay(10);
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

