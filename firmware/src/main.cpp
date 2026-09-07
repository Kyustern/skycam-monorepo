#include <AccelStepper.h>
#include <MultiStepper.h>
#include <Arduino.h>
#include <avr/wdt.h>
#include <pins.h>

#define _LED_BUILTIN_ 27

#define M_MAX_SPEED 500.0
#define M_SPEED 500.0
#define M_ACCEL 100.0

// #define YAW_STEP_PIN 15
#define YAW_STEP_PIN 15
#define YAW_DIR_PIN 21
#define YAW_LIMIT_PIN 18

#define PITCH_STEP_PIN 22
#define PITCH_DIR_PIN 23
#define PITCH_LIMIT_PIN 19

#define XYE_ENABLE 14
#define FAN 4

#define BUTTON 20
// 84/18 teeth
const float gear_ratio = 4.666666667;
const float yaw_degs_per_steps = 1.8;
const float pitch_degs_per_steps = 1.8;
//We substract 30 degrees to avoid hitting the limit switch
float SAFETY_RANGE_MULTIPLIER = (360-30) / 360.0f;
float yaw_abs_max = ((180 / 1.8) * 16 * gear_ratio);
float yaw_safe_range = yaw_abs_max * SAFETY_RANGE_MULTIPLIER;
int yaw_dir = -1;
float pitch_abs_max = ((180 / 1.8) * 16 * gear_ratio);
float pitch_safe_range = pitch_abs_max * SAFETY_RANGE_MULTIPLIER;
int pitch_dir = 1;

float steps_safety_offset = (1.0f - SAFETY_RANGE_MULTIPLIER) * yaw_abs_max;
float middle = yaw_abs_max / 2.0f;

AccelStepper YAW_STEPPER(AccelStepper::DRIVER, YAW_STEP_PIN, YAW_DIR_PIN);
AccelStepper PITCH_STEPPER(AccelStepper::DRIVER, PITCH_STEP_PIN, PITCH_DIR_PIN);

MultiStepper STEPPERS;

enum HomingState
{
    IDLE,
    HOMING_YAW,
    HOMING_PITCH
};
enum OperationState
{
    OP_IDLE,
    OP_MOVING
};

enum MotorsEnableState
{
    MOT_ENABLED,
    MOT_DISABLED
};
enum DIRECTION
{
    CW,
    CCW
};

// Runtime variables

OperationState operationState = OperationState::OP_IDLE;
HomingState homingState = IDLE;
unsigned long lastLedToggle = 0;
bool ledState = LOW;

int getSafePosition(int target) {
  int direction = target > 0 ? 1 : -1;
  int abs_target = target;
  int lower_thresh = (steps_safety_offset / 2.0f) * direction;
  int upper_thresh = yaw_abs_max - ((steps_safety_offset / 2.0f) * direction);

  if (target > 0)
  {
    return min(target, yaw_abs_max - (steps_safety_offset / 2.0f));
  } else {
    return max(target, (steps_safety_offset / 2.0f) + yaw_abs_max);
  }
  

  // return max(lower_thresh, min(upper_thresh, abs_target));
}

int degreesToStep(int axis_full_steps, float target_degrees) {
    // int steps_target = map(0, 360, 0, yaw_full_range, target_degrees);
    int safe_stesps_target = getSafePosition(target_degrees);
    return safe_stesps_target;
}

void setMotorsEn(MotorsEnableState desiredState)
{
    switch (desiredState)
    {
    case MOT_ENABLED:
        Serial.println("Motors enabled");
        digitalWrite(XYE_ENABLE, LOW);
        break;
    case MOT_DISABLED:
        Serial.println("Motors disabled");
        digitalWrite(XYE_ENABLE, HIGH);
        break;

    default:
        break;
    }
}

// void safeMove(AccelStepper& stepper, int direction, float target) {
//   int abs_target = abs(target);
//   int lower_thresh = steps_safety_offset / 2.0f;
//   int upper_thresh = yaw_full_range - (steps_safety_offset / 2.0f);

//   int l = max(lower_thresh, abs_target);
//   int u = min(upper_thresh, l);

//   return u;

//   int min = max(abs_target)
//   if (abs_target > (steps_safety_offset / 2.0f) && abs_target < (yaw_full_range - (steps_safety_offset / 2.0f))) {
//   }
// }

void homeMotor(AccelStepper& stepper, int limitSwitchPin, const char* motorName, int direction)
{
    stepper.setMaxSpeed(M_SPEED);
    stepper.setAcceleration(M_ACCEL);
    stepper.setSpeed(M_SPEED);

    Serial.print("Homing ");
    Serial.print(motorName);
    Serial.println("...");

    // Move towards the limit switch until it reads HIGH
    stepper.move(yaw_abs_max * (direction > 0 ? -1 : 1));
    while (digitalRead(limitSwitchPin) != HIGH)
    {
        stepper.run();
    }

    
    stepper.setCurrentPosition(direction * yaw_abs_max);
    stepper.stop();
    int s = (steps_safety_offset / 2) * direction;
    Serial.print("steps_safety_offset : "); Serial.println(steps_safety_offset);
    Serial.print("stepper.currentPosition : "); Serial.println(stepper.currentPosition());
    Serial.print("s : "); Serial.println(s);
    stepper.move(s);
    stepper.runToPosition();
    
    stepper.stop();

    Serial.print(motorName);
    Serial.println(" homed.");
    Serial.print("Current position : ");
    Serial.println(stepper.currentPosition());
}

void moveToPosition(float yawAngle, float pitchAngle) {
    setMotorsEn(MotorsEnableState::MOT_ENABLED);
    operationState = OperationState::OP_MOVING;

    //Map test
    int safe = yaw_abs_max - steps_safety_offset;
    Serial.print("safe : "); Serial.println(safe);
    int yawMapped = map(yawAngle, -180, 180, -safe, safe);
    int pitchMapped = map(pitchAngle, -180, 180, -safe, safe);
    Serial.print("yawMapped : "); Serial.println(yawMapped);
    YAW_STEPPER.moveTo(yawMapped);
    PITCH_STEPPER.moveTo(pitchMapped);
    // Convert degrees to steps
    // 0-360 degrees maps to 0-axis_full_range steps
    // float yawOffset = yaw_abs_max * ((15.0f/360.0f));
    // const int pitchOffset = abs(middle - 7819);
    // int yawSteps = static_cast<int>((yawAngle / 360.0) * yaw_abs_max);
    // int pitchSteps = static_cast<int>((pitchAngle / 360.0) * pitch_abs_max);

    // // Apply safety limits and move
    // int safe_yaw = getSafePosition(yawSteps + yawOffset) * yaw_dir;
    // Serial.print("safe_yaw : "); Serial.println(safe_yaw);
    // YAW_STEPPER.moveTo(safe_yaw);
    // int safe_pitch = getSafePosition(pitchSteps + pitchOffset) * pitch_dir;
    // Serial.print("safe_pitch : "); Serial.println(safe_pitch);
    // PITCH_STEPPER.moveTo(safe_pitch);
    // PITCH_STEPPER.moveTo(getSafePosition(pitchSteps + pitchOffset) * pitch_dir);
}

void setup()
{
    // Initialize LED first for status indication
    pinMode(_LED_BUILTIN_, OUTPUT);
    
    // Blink LED during setup to indicate initialization
    for (int i = 0; i < 3; i++) {
        digitalWrite(_LED_BUILTIN_, HIGH);
        delay(100);
        digitalWrite(_LED_BUILTIN_, LOW);
        delay(100);
    }
    
    Serial.begin(9600);
    delay(100);  // Allow serial to initialize
    Serial.println("Controller start");
    pinMode(YAW_LIMIT_PIN, INPUT_PULLUP);
    pinMode(PITCH_LIMIT_PIN, INPUT_PULLUP);
    pinMode(XYE_ENABLE, OUTPUT);
    // pinMode(FAN, OUTPUT);
    pinMode(BUTTON, INPUT);

    setMotorsEn(MOT_ENABLED);

    homeMotor(YAW_STEPPER, YAW_LIMIT_PIN, "YAW", yaw_dir);
    homeMotor(PITCH_STEPPER, PITCH_LIMIT_PIN, "PITCH", pitch_dir);
    
    STEPPERS.addStepper(YAW_STEPPER);
    STEPPERS.addStepper(PITCH_STEPPER);

    Serial.println("All motors homed, entering operation status");

    moveToPosition(0.0, 0.0);

}

void sendSerial() {

}

void checkSerial() // method for receiving the commands
{
    static String serialBuffer = "";

    // Read all available data from serial
    while (Serial.available() > 0) {
        char c = Serial.read();
        // Check for end of line (newline or carriage return)
        if (c == '\n' || c == '\r') {
            if (serialBuffer.length() > 0) {
                // Process complete command
                if (serialBuffer == "n") {
                    PITCH_STEPPER.stop();
                    PITCH_STEPPER.disableOutputs();
                    YAW_STEPPER.stop();
                    YAW_STEPPER.disableOutputs();
                    Serial.println("STOPPED ALL STEPPERS");
                }
                else if (serialBuffer.startsWith("moveto")) {
                    // Extract parameters (everything after "moveto")
                    String params = serialBuffer.substring(6);
                    params.trim();

                    // Find the space separating the two values
                    int spaceIndex = params.indexOf(' ');
                    if (spaceIndex > 0 && spaceIndex < params.length() - 1) {
                        String yawStr = params.substring(0, spaceIndex);
                        String pitchStr = params.substring(spaceIndex + 1);
                        pitchStr.trim();

                        // Parse floats
                        float yawAngle = yawStr.toFloat();
                        float pitchAngle = pitchStr.toFloat();

                        if (!isnan(yawAngle) && !isnan(pitchAngle)) {
                            moveToPosition(yawAngle, pitchAngle);
                        } else {
                            Serial.println("Error: moveto requires two valid float values");
                        }
                    } else {
                        Serial.println("Error: moveto requires two float arguments (e.g., 'moveto 45.00 90.00')");
                    }
                }
                else {
                    Serial.print("Received odd command: ");
                    Serial.println(serialBuffer);
                }
                serialBuffer = ""; // Clear buffer for next command
            }
        } else {
            // Add character to buffer
            serialBuffer += c;
        }
    }
}

void loop()
{
    checkSerial();
    if (digitalRead(BUTTON) == HIGH)
    {
        wdt_enable(WDTO_15MS);
        while (1)
        {
        }
    }
    YAW_STEPPER.run();
    PITCH_STEPPER.run();

    // Non-blocking LED blink at 2Hz (toggle every 250ms)
    if (millis() - lastLedToggle >= 500) {
        lastLedToggle = millis();
        ledState = !ledState;
        digitalWrite(_LED_BUILTIN_, ledState);
    }

    if (YAW_STEPPER.distanceToGo() == 0 && PITCH_STEPPER.distanceToGo() == 0) {

        if (operationState == OperationState::OP_MOVING)
        {
            operationState = OperationState::OP_IDLE;
            setMotorsEn(MotorsEnableState::MOT_DISABLED);
            while (!Serial.availableForWrite()) {}
            uint8_t checkmark[] = {0xE2, 0x9C, 0x93}; // UTF-8 encoding for ✓
            Serial.write(checkmark, sizeof(checkmark));
        }
        //Stress test
        // if (currentPos == 0) {
        //     moveToPosition(180.0, 180.0);
        //     currentPos = 1;
        // } else {
        //     moveToPosition(90.0, 90.0);
        //     currentPos = 0;
        // }
    }
}
