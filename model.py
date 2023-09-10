from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam

import numpy as np
import random
import gym
import os


class DecayObject:
    def __init__(self, initial_value, minimum, rate):
        self.initial_value = initial_value
        self.value = initial_value
        self.minimum = minimum
        self.rate = rate

    def __call__(self):
        self.value = max(self.minimum, self.value*self.rate)
        return self.value

    def __repr__(self):
        return f"Decay({self.initial_value}, {self.minimum}, {self.rate})"


class NeuralNetwork:
    def __init__(self, name):
        self.is_compiled = False
        self.model = None

        self.name = name
        self.path = self.name + ".keras"
        self.temp_path = self.name + "-temp.keras"

    @property
    def exists(self):
        return os.path.exists(self.path)

    def build_model(self, input_dim, output_dim):
        self.model = Sequential()
        self.model.add(Dense(input_dim, activation='relu', input_dim=input_dim))
        self.model.add(Dense(input_dim*2, activation='relu'))
        self.model.add(Dense(input_dim, activation='relu'))
        self.model.add(Dense(output_dim, activation='sigmoid'))
        return self.model

    def compile(self, optimizer='adam', loss='mean_squared_error', **kwargs):
        self.model.compile(optimizer=optimizer, loss=loss, **kwargs)
        self.is_compiled = True
        return self

    def fit(self, X, y, **kwargs):
        assert self.is_compiled, "First, you must compile the model!"
        self.model.fit(X, y, **kwargs)
        return self

    def predict(self, X, **kwargs):
        return self.model.predict(X, **kwargs)

    def save(self, temp=False):
        if temp:
            self.model.save_model(self.temp_path)
        else:
            self.model.save_model(self.path)

    def load(self, temp=False):
        if temp:
            self.model = load_model(self.temp_path)
        else:
            self.model.save_model(self.path)

    def __call__(self):
        return self.model


class Agent:
    def __init__(self, env, tau=.125, gamma=.03, lr=.005):
        self.env = env
        self.tau = tau
        self.gamma = gamma
        self.learning_rate = lr
        self.history = []

        self.epsilon = DecayObject(1, .01, .95)

        self.base_model = NeuralNetwork('base_model')
        self.base_model.build_model(
            input_dim=self.env.observation_space.shape[0],
            output_dim=self.env.action_space.n
        )
        self.base_model.compile(optimizer=Adam(learning_rate=self.learning_rate))

        self.target_model = NeuralNetwork('target_model')
        self.target_model.build_model(
            input_dim=self.env.observation_space.shape[0],
            output_dim=self.env.action_space.n
        )
        self.target_model.compile(optimizer=Adam(learning_rate=self.learning_rate))

    def train(self, epochs=100, max_tries=50, render=False):
        for epoch in range(1, epochs+1):
            state = self.env.reset().reshape(1, 2)

            for t in range(max_tries):
                print('#', epoch, '=>', t)
                if render:
                    self.env.render()

                action = self.get_action(state)
                new_state, reward, done, *info = self.env.step(action)
                new_state = new_state.reshape(1, 2)

                self.history.append([state, action, reward, new_state, done])
                self.train_base()
                # TODO: train target by a delay
                self.train_target()

                state = new_state
                if done:
                    break

    # TODO: separate each step of training in train_step()
    def train_step(self):
        pass

    def train_base(self, batch_size=32):
        for state, action, reward, new_state, done in random.sample(self.history, min(batch_size, len(self.history))):
            target = self.target_model.predict(state)

            if not done:
                Q_future = max(self.target_model.predict(new_state)[0])
                reward += (Q_future * self.gamma)

            target[0][action] = reward

            self.base_model.fit(state, target, epochs=2, verbose=0)

    def train_target(self):
        base_weights = self.base_model().get_weights()
        target_weights = self.target_model().get_weights()
        for i in range(len(target_weights)):
            target_weights[i] = (base_weights[i] * self.tau) + (target_weights[i] * (1-self.tau))

        self.target_model.set_weights(target_weights)

    def get_action(self, state):
        if np.random.random() < self.epsilon():
            return self.env.action_space.sample()
        return np.argmax(self.base_model.predict(state)[0])

    def load_models(self, temp=False):
        if self.base_model.exists:
            self.base_model.load(temp=temp)

        if self.target_model.exists:
            self.target_model.load(temp=temp)

    def save_models(self, temp=False):
        self.base_model.save(temp=temp)
        self.target_model.save(temp=temp)



if __name__ == '__main__':
    env = gym.make('MountainCar-v0')
    env.reset()

    agent = Agent(env)
    agent.load_models()
    agent.train(epochs=5)
    agent.save_models()
