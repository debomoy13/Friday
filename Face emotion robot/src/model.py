
import tensorflow as tf
"""First Baseline model"""
model=tf.keras.Sequential(
    [
        tf.keras.Input(shape=(48,48,1)),

        tf.keras.layers.Conv2D(32,kernel_size=3,activation='relu', padding='same'),
        tf.keras.layers.MaxPool2D(),

        tf.keras.layers.Conv2D(64,kernel_size=3,activation='relu'),
        tf.keras.layers.MaxPool2D(),

        tf.keras.layers.Conv2D(128, kernel_size=3,activation='relu'),
        tf.keras.layers.MaxPool2D(),

        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(128, activation='relu'),

        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(5,actication='softmax')
        ])
model.summary()