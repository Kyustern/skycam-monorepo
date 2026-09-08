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
//We subtract 15 degrees from each end (30 degrees total) to avoid hitting the limit switch
const float SAFETY_DEGREES = 15.0f; // Safety margin from each end
const float TOTAL_SAFETY_DEGREES = 30.0f; // Total safety margin

float yaw_abs_max = ((360 / 1.8) * 16 * gear_ratio);
float pitch_abs_max = ((360 / 1.8) * 16 * gear_ratio);

// Calculate steps for safety margin (15 degrees on each end)
// Steps per degree: yaw_abs_max / 360.0f
float steps_per_degree = yaw_abs_max / 360.0f;
float steps_safety_offset = SAFETY_DEGREES * steps_per_degree; // Steps for 15 degrees

// For bipolar range: -yaw_abs_max/2 to +yaw_abs_max/2
float yaw_max_positive = yaw_abs_max / 2.0f;
float yaw_max_negative = -yaw_abs_max / 2.0f;
float pitch_max_positive = pitch_abs_max / 2.0f;
float pitch_max_negative = -pitch_abs_max / 2.0f;

// Safe range limits for bipolar setup
float yaw_safe_max = yaw_max_positive - steps_safety_offset;
float yaw_safe_min = yaw_max_negative + steps_safety_offset;
float pitch_safe_max = pitch_max_positive - steps_safety_offset;
float pitch_safe_min = pitch_max_negative + steps_safety_offset;

int yaw_dir = -1;
int pitch_dir = 1;

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

// Clamp target position to safe bipolar range
float getSafePosition(float target, float safe_min, float safe_max) {
  // For bipolar range: clamp between safe_min and safe_max
  if (target > safe_max) {
    return safe_max;
  } else if (target < safe_min) {
    return safe_min;
  }
  return target;
}

// Convert degrees to steps for bipolar range
float degreesToSteps(float target_degrees, float axis_max_steps) {
    // Map from -180 to +180 degrees to -axis_max_steps/2 to +axis_max_steps/2
    return (target_degrees / 360.0f) * axis_max_steps;
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

void homeMotor(AccelStepper& stepper, int limitSwitchPin, const char* motorName, int direction, float axis_max_steps) {
    stepper.setMaxSpeed(M_SPEED);
    stepper.setAcceleration(M_ACCEL);
    stepper.setSpeed(M_SPEED);

    Serial.print("Homing ");
    Serial.print(motorName);
    Serial.println("...");

    // Determine which physical limit we're homing to
    // For bipolar range: 
    // - axis_max_steps/2 represents one physical end
    // - -axis_max_steps/2 represents the other physical end
    // We move in the direction that will hit the limit switch
    
    float limit_position = (direction > 0) ? -axis_max_steps / 2.0f : axis_max_steps / 2.0f;
    
    // Move towards the limit switch until it reads HIGH
    // Use a large move to ensure we hit the limit from any starting position
    stepper.move(limit_position * 2);
    while (digitalRead(limitSwitchPin) != HIGH)
    {
        stepper.run();
    }

    // Set current position to the physical limit we just hit
    stepper.setCurrentPosition(limit_position);
    stepper.stop();
    
    // Move back from the limit by safety offset to avoid hitting it during normal operation
    // For direction = -1 (YAW): move from +limit towards center by safety offset
    // For direction = +1 (PITCH): move from -limit towards center by safety offset
    float safe_position = limit_position + (steps_safety_offset * direction);
    
    Serial.print("steps_safety_offset : "); Serial.println(steps_safety_offset);
    Serial.print("stepper.currentPosition : "); Serial.println(stepper.currentPosition());
    Serial.print("safe_position : "); Serial.println(safe_position);
    stepper.moveTo(safe_position);
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

    // Convert angles to steps using bipolar range
    // Map from -180 to +180 degrees to -yaw_abs_max/2 to +yaw_abs_max/2
    float yawSteps = degreesToSteps(yawAngle, yaw_abs_max);
    Serial.print("yawSteps : "); Serial.println(yawSteps);
    // float pitchSteps = degreesToSteps(pitchAngle, pitch_abs_max) - 7819;
    float pitchSteps = degreesToSteps(pitchAngle, pitch_abs_max);
    Serial.print("pitchSteps : "); Serial.println(pitchSteps);
    
    // Apply safety limits for each axis
    float safeYawSteps = getSafePosition(yawSteps, yaw_safe_min, yaw_safe_max);
    float safePitchSteps = getSafePosition(pitchSteps, pitch_safe_min, pitch_safe_max);
    
    // Apply direction multipliers
    YAW_STEPPER.moveTo(safeYawSteps * yaw_dir);
    PITCH_STEPPER.moveTo(safePitchSteps * -1);
}

void setup()
{

    Serial.print("yaw_abs_max : "); Serial.println(yaw_abs_max);


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

    homeMotor(YAW_STEPPER, YAW_LIMIT_PIN, "YAW", yaw_dir, yaw_abs_max);
    homeMotor(PITCH_STEPPER, PITCH_LIMIT_PIN, "PITCH", pitch_dir, pitch_abs_max);
    
    STEPPERS.addStepper(YAW_STEPPER);
    STEPPERS.addStepper(PITCH_STEPPER);

    Serial.println("All motors homed, entering operation status");

    // moveToPosition(0.0, 0.0);q
    moveToPosition(180.0, 180.0);

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
