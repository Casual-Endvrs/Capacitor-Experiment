float R = 2200; // resistance of the resistor
float C = 220e-6; // 0.01; // 220e-6; // capacitance of the capacitor
float tc = R*C; // time constant of the circuit
int exp_dur = 7; // duration of the experiment as a multiple of tc
int steps_per_tc = 50; // number of steps per tc

int pulse_width_ms = 100; // duration of pulse
int pulse_duty_cycle = 50; // percent duty cycle of the pulse

float Vcc = 5.0;
const int measure_volt = A0; // pin used to measure voltage across capacitor
float cap_volt = 0; // measured voltage across the capacitor

String serial_command; // command to run from pc
String serial_bit; // part of pc command
String cmd; // parsed command from pc
String param; // parsed parameter from pc

int idx; // index of character

void setup() {
  Serial.begin(230400);
  pinMode(8, OUTPUT);
  digitalWrite(8, LOW);
  Serial.setTimeout(1);
}

void loop() {
  serial_command = "";
  while (!Serial.available()) {}
  while (Serial.available()) {
    if (false) { serial_command = Serial.readString(); }
    else if (true) { serial_command = Serial.readStringUntil('/'); }
    else {
      while (true) {
        serial_bit = Serial.readString();
        serial_command.concat( serial_bit );
        idx = serial_command.indexOf('/');
        if (idx != -1) {
          break;
        }
      }
    }
  }
  
  idx = serial_command.indexOf(';');

  if (idx != -1) {
    param = serial_command.substring(idx+1);
    cmd = serial_command.substring(0, idx);
  } else {
    cmd = serial_command;
  }
  
  //if (cmd=="ce") { run_exp(1); } // start charging experiment
  //else if (cmd=="de") { run_exp(0); } // start discharging experiment
  //else if (cmd=="prep_discharge") { digitalWrite(8, LOW); Serial.println(1); } // prep - set pin low
  //else if (cmd=="prep_charge") { digitalWrite(8, HIGH); Serial.println(1); } // prep - set pin high
  
  //else if (cmd=="get_pin_state") { Serial.println(digitalRead(8)); } // get pin state used to charge/discharge the capacitor
  
  //else if (cmd=="set_R") { R = param.toFloat(); Serial.println(1); } // set resistance
  //else if (cmd=="get_R") { Serial.println(R); } // get resistance
  //else if (cmd=="set_C") { C = param.toFloat(); Serial.println(1); } // set capacitance
  //else if (cmd=="get_C") { Serial.println(C); } // get capacitance
  //else if (cmd=="set_Vcc") { Vcc = param.toFloat(); Serial.println(1); } // set Vcc
  //else if (cmd=="get_Vcc") { Serial.println(Vcc); } // get get_Vcc
  //else if (cmd=="set_num_tcs") { exp_dur = param.toFloat(); Serial.println(1); } // set experiment duration as a factor * tc
  //else if (cmd=="get_num_tcs") { Serial.println(exp_dur); } // get experiment duration as a factor * tc
  //else if (cmd=="set_steps_per_tc") { steps_per_tc = param.toInt(); Serial.println(1); } // set steps / tc
  //else if (cmd=="get_steps_per_tc") { Serial.println(steps_per_tc); } // get steps / tc
  //else if (cmd=="get_cap_v") { Serial.println(Vcc*analogRead(A0)/1023); } // get current capacitor voltage

  //else if (cmd=="freq_exp") { freq_exp(); } // frequency experiment
  //else if (cmd=="set_pw_dur") { pulse_width_ms = param.toInt(); Serial.println(1); } // set pulse width duration
  //else if (cmd=="get_pw_dur") { Serial.println(pulse_width_ms); } // get pulse width duration
  //else if (cmd=="set_pw_dc") { pulse_duty_cycle = param.toInt(); Serial.println(1); } // set pulse width duty cycle
  //else if (cmd=="get_pw_dc") { Serial.println(pulse_duty_cycle); } // get pulse width duty cycle
  
  //else if (cmd=="test_connection") { Serial.println("good_connection"); } // test connection
  
  if (cmd=="a") { run_exp(1); } // start charging experiment
  else if (cmd=="b") { run_exp(0); } // start discharging experiment
  else if (cmd=="c") { digitalWrite(8, LOW); Serial.println(1); } // prep - set pin low
  else if (cmd=="d") { digitalWrite(8, HIGH); Serial.println(1); } // prep - set pin high
  
  else if (cmd=="e") { Serial.println(digitalRead(8)); } // get pin state used to charge/discharge the capacitor
  
  else if (cmd=="f") { R = param.toFloat(); Serial.println(1); } // set resistance
  else if (cmd=="g") { Serial.println(R); } // get resistance
  else if (cmd=="h") { C = param.toFloat(); Serial.println(1); } // set capacitance
  else if (cmd=="i") { Serial.println(1e6*C); } // get capacitance
  else if (cmd=="j") { Vcc = param.toFloat(); Serial.println(1); } // set Vcc
  else if (cmd=="k") { Serial.println(Vcc); } // get get_Vcc
  else if (cmd=="l") { exp_dur = param.toInt(); Serial.println(1); } // set experiment duration as a factor * tc
  else if (cmd=="m") { Serial.println(exp_dur); } // get experiment duration as a factor * tc
  else if (cmd=="n") { steps_per_tc = param.toInt(); Serial.println(1); } // set steps / tc
  else if (cmd=="o") { Serial.println(steps_per_tc); } // get steps / tc
  else if (cmd=="p") { Serial.println(Vcc*analogRead(A0)/1023); } // get current capacitor voltage

  else if (cmd=="q") { freq_exp(); } // frequency experiment
  else if (cmd=="r") { pulse_width_ms = param.toInt(); Serial.println(1); } // set pulse width duration
  else if (cmd=="s") { Serial.println(pulse_width_ms); } // get pulse width duration
  else if (cmd=="t") { pulse_duty_cycle = param.toInt(); Serial.println(1); } // set pulse width duty cycle
  else if (cmd=="u") { Serial.println(pulse_duty_cycle); } // get pulse width duty cycle
  
  else if (cmd=="v") { verify_cap_discharged(true); } // verify the capacitor is discharged
  else if (cmd=="w") { verify_cap_charged(true); } // verify the capacitor is charged
  
  else if (cmd=="x") { dis_charge_cap(1); } // charge capacitor with data returned
  else if (cmd=="y") { dis_charge_cap(0); } // discharge capacitor with data returned
  
  else if (cmd=="z") { set_pwr_low(); } // set pin powering capacitor LOW
  
  else if (cmd=="test_connection") { Serial.println("good_connection"); } // test connection
  
  
  // experimenting functions
  else if (cmd=="led_exp") { led_exp(); }
  else if (cmd=="test_fn") { test_micros(); }
}

void run_exp( int exp_type) {
  //if (exp_type == 1) { verify_cap_charged(false); }
  //else { verify_cap_discharged(false); }
  
  unsigned long next_t = micros(); // next time for measurement
  int dt = 1000.0; // minimum time between each measurement
  
  unsigned long t;
  float cap_V;

  unsigned long t_exp_end = micros() + float(R*C*exp_dur)*float(1000)*float(1000);

  digitalWrite(8, exp_type);
  while (true) {
    t = micros();
    if (t >= next_t) {
      cap_V = Vcc * analogRead(A0) / 1023;
      Serial.print( t );
      Serial.print( ',' );
      Serial.println( cap_V );
      next_t += dt;
    }
    if (t > t_exp_end) { break; }
  }
  Serial.println( "end" );
}

void freq_exp() {
  // pulse width is a duration of time in microseconds
  // duty_cycle is a percent of duty cycle to remain on
  unsigned long t_current; // current time
  unsigned long next_t_measure = micros(); // next time for measurement
  unsigned long next_t_pulse = micros(); // next time for pulse switch
  unsigned long next_serial_check = micros(); // next time to check serial for stop command
  int dt_measure = 1 * 1000; // minimum time between each measurement
  
  long dt_on = long(pulse_width_ms) * long(pulse_duty_cycle) * 10; // duration to set output HIGH
  long dt_off = long(pulse_width_ms) * (100 - long(pulse_duty_cycle)) * 10; // duration to set output LOW

  unsigned long dt_serial_check = long(250) * long(1000);
  
  float cap_V;
  bool pin_state = false;
  
  while (true) {
    t_current = micros();
    if (t_current >= next_t_measure) {
      cap_V = Vcc * analogRead(A0) / 1023;
      Serial.print( t_current );
      Serial.print( ',' );
      Serial.println( cap_V );
      next_t_measure += dt_measure;
    }
    if (t_current >= next_t_pulse) {
      pin_state = !pin_state;
      digitalWrite(8, pin_state);
      if (pin_state) { next_t_pulse += dt_on; }
      else {next_t_pulse += dt_off; }
    }
    if (t_current >= next_serial_check) {
      cmd = Serial.readStringUntil('/');
      if (cmd=="stop") { break; }
      next_serial_check += dt_serial_check;
    }
  }
  Serial.println( "end" );
}

void dis_charge_cap(int exp_type) {
  //if (exp_type == 1) { verify_cap_charged(false); }
  //else { verify_cap_discharged(false); }
  
  unsigned long t_now = micros(); // time at start of loop
  unsigned long t_measure_next = micros(); // time for next measurement
  int dt_measure = 1000; // minimum time between each serial check
  
  unsigned long t_check_serial = micros(); // time to check serial
  unsigned long dt_serial_check = long(250) * long(1000); // minimum time between each serial check

  float cap_V;
  
  while(true) {
    t_now = micros();
    if(t_now >= t_measure_next) {
      cap_V = Vcc * analogRead(A0) / 1023;
      Serial.print( t_now );
      Serial.print( ',' );
      Serial.println( cap_V );
      t_measure_next += dt_measure;
    }
    if(t_now >= t_check_serial) {
      cmd = Serial.readStringUntil('/');
      if (cmd=="stop") { break; }
      t_check_serial += dt_serial_check;
    }
  }
}

void verify_cap_discharged(bool serial_return) {
  //if(serial_return) { Serial.println("0"); } // signal process started
  digitalWrite(8, LOW);
  int cap_v;

  long t = millis();
  
  while(true) {
    if(millis()>t) {
      t += 5;
      cap_v = analogRead(A0);
      Serial.println( Vcc*cap_v/1023 );
      if (cap_v < 3) { Serial.println("end"); break; }
    }
  }
  Serial.println("end");
  //if(serial_return) { Serial.println("1"); } // signal process complete
}

void verify_cap_charged(bool serial_return) {
  //if(serial_return) { Serial.println("0"); } // signal process started
  digitalWrite(8, HIGH);
  int cap_v;

  long t = millis();
  
  while(true) {
    if(millis()>t) {
      t += 5;
      cap_v = analogRead(A0);
      Serial.println( Vcc*cap_v/1023 );
      if (cap_v > 1018) { Serial.println("end"); break; }
    }
  }
  Serial.println("end");
  //if(serial_return) { Serial.println("1"); } // signal process complete
}

void set_pwr_low() { digitalWrite(8, LOW); }























void run_exp_samples( int exp_type) {
  //if (exp_type == 1) { verify_cap_charged(false); }
  //else { verify_cap_discharged(false); }
  
  tc = R*C;
  
  const int total_num_data_points = 2*exp_dur*steps_per_tc; // total number of data points to collect for the experiment

  int itr = 0; // experiment iteration number, advanced upon data aquisition only
  unsigned long next_t = micros(); // next time for measurement
  int dt = 1000.0*1000.0*float(tc)/float(steps_per_tc); // minimum time between each measurement
  
  unsigned long t;
  float cap_V;

  digitalWrite(8, exp_type);
  while (true) {
    t = micros();
    if (t >= next_t) {
      cap_V = Vcc * analogRead(A0) / 1023;
      Serial.print( t );
      Serial.print( ',' );
      Serial.println( cap_V );
      itr += 1;
      next_t += dt;
    }
    if (itr >= total_num_data_points) { break; }
  }
  Serial.println( "end" );
}






// experimenting functions

void test_micros() {
  unsigned long t_prev = micros();
  unsigned long t_now = micros();
  while (true) {
    t_prev = t_now;
    t_now = micros();
    Serial.println( t_now );
  }
}

void led_exp() {
  unsigned long t_next = millis();
  pinMode(13, OUTPUT);
  int dt = 1000;
  bool pin_mode = false;
  
  int step_num = 0;
  
  unsigned long t_check_serial = millis();
  unsigned int dt_check_serial = 100;
  while (true) {
    if (millis() >= t_check_serial) {
      Serial.print("step_num : ");
      Serial.println( step_num );
      step_num += 1;
      cmd = Serial.readStringUntil('/');
      if (cmd=="stop") { Serial.println("breaking"); break; }
      t_check_serial += dt_check_serial;
    }
    if (millis() >= t_next) {
      Serial.println("switching state");
      pin_mode = not pin_mode;
      digitalWrite(13, pin_mode);
      t_next += dt;
    }
  }
}
