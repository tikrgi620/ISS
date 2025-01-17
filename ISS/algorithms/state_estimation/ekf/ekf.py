import numpy as np
from ISS.algorithms.utils.angle import pi_2_pi

DEBUG_MSGS = False
class EKF:
    EARTH_RADIUS = 6378135 # Equator radius

    def __init__(self, settings) -> None:
        self._dt = 1 / settings['frequency']
        self._vehicle_info = settings['vehicle_info']
        self._state = np.zeros(5)
        self._SIGMA = np.eye(5) * 1e-5  # Adjusted initialization
        self._R = np.eye(5) * 1e-5  # Process noise covariance
        self._Q = np.eye(5) * 1e-5  # Measurement noise covariance
        self._H = np.eye(5)  # Measurement matrix
        self._G = None
        self._is_initialized = False

    def initialize(self, obs_x, obs_y, obs_yaw, speed, acc_x, x_std, y_std, obs_yaw_std, speed_std, acc_x_std):
        self._state = np.array([obs_x, obs_y, obs_yaw, speed, acc_x])
        self._Q = np.diag([x_std**2, y_std**2, obs_yaw_std**2, speed_std**2, acc_x_std**2])
        self._is_initialized = True
    
    def is_initialized(self):
        return self._is_initialized
    
    def step(self, acc_x, obs_yaw, obs_x, obs_y, speed, steer):
        assert self._is_initialized, "EKF is not initialized"
        obs_yaw = pi_2_pi(obs_yaw - self._state[2]) + self._state[2]
        # Update the state with the bicycle model
        # print("previous angle: ", self._state[2])
        self.bicycle_model_step(acc_x, steer)
        # print("steer: ", steer)
        # print("predicted angle: ", self._state[2])
        # print("observed angle: ", obs_yaw)
        if DEBUG_MSGS:
            print("-------------------")
            print("predicted state: ", self._state)
        # Calculate the Jacobian of the motion model
        self._G = self.calculate_jacobian(self._state, steer, acc_x)
        # Predict the error covariance
        self._SIGMA = self._G @ self._SIGMA @ self._G.T + self._R
        # Calculate the Kalman Gain
        K = self._SIGMA @ self._H.T @ np.linalg.inv(self._H @ self._SIGMA @ self._H.T + self._Q)
        # Update the state with the new measurements
        z = np.array([obs_x, obs_y, obs_yaw, speed, acc_x])
        if DEBUG_MSGS:
            print("observed state: ", z)
        # print("added term: ", (K @ (z - self._H @ self._state))[2])
        self._state = self._state + K @ (z - self._H @ self._state)
        self._state[2] = pi_2_pi(self._state[2])
        # print("updated angle: ", self._state[2])
        # Update the error covariance
        self._SIGMA = (np.eye(5) - K @ self._H) @ self._SIGMA
        if DEBUG_MSGS:
            print("updated state: ", self._state)
        return self._state

    def calculate_jacobian(self, state, steer, acc_x):
        x, y, theta, v, _ = state
        dt = self._dt
        L = self._vehicle_info['wheelbase']
        F = np.array([
            [1, 0, -v*np.sin(theta)*dt, np.cos(theta)*dt, 0],
            [0, 1, v*np.cos(theta)*dt, np.sin(theta)*dt, 0],
            [0, 0, 1, np.tan(steer)/L*dt, 0],
            [0, 0, 0, 1, dt],
            [0, 0, 0, 0, 1]
        ])
        return F

    def bicycle_model_step(self, acc_x, steer):
        if DEBUG_MSGS:
            print("acc_x: ", acc_x)
        x, y, theta, v, _ = self._state
        dt = self._dt
        L = self._vehicle_info['wheelbase']
        self._state[0] += v * np.cos(theta) * dt
        self._state[1] += v * np.sin(theta) * dt
        self._state[2] += (v * np.tan(steer) / L * dt)
        self._state[3] += acc_x * dt
        # Assuming constant acceleration within this step
        self._state[4] = acc_x
        
    def get_state(self):
        return self._state.tolist()
    
    def geo_to_xy(self, lat, lon):
        # https://github.com/carla-simulator/carla/issues/3871
        lat_rad = (np.deg2rad(lat) + np.pi) % (2 * np.pi) - np.pi
        lon_rad = (np.deg2rad(lon) + np.pi) % (2 * np.pi) - np.pi
        x = EKF.EARTH_RADIUS * np.sin(lon_rad) * np.cos(lat_rad) 
        y = EKF.EARTH_RADIUS * np.sin(-lat_rad)
        return x, y