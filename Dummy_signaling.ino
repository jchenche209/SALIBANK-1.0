char serialData;
int pin=10; // dummy pin for function.

void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(pin, OUTPUT);
  Serial.begin(9600); // opens serial port, sets data rate to 9600 bps
}

// the loop function runs over and over again forever
void loop() {
  // standby for signal
  if (Serial.available() > 0){
    serialData = Serial.read();
    Serial.print(serialData);

    if(serialData =='0'){ // deposit kit
      delay(2000);
      Serial.println("depositado");
      }
      
    else if (serialData == '1'){ // open sample deposition window
      delay(3000);
      Serial.println("guardado");
      }
  }
}
