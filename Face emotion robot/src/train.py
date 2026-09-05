import os
import matplotlib.pyplot as plt
from model import model
import tensorflow as tf

train_dir="data/split/train"
val_dir="data/split/val"
test_dir="data/split/test"

train_ds = tf.keras.utils.image_dataset_from_directory(
    train_dir,
    image_size=(48, 48),
    color_mode="grayscale",
    batch_size=32,
    shuffle=True
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    val_dir,
    image_size=(48, 48),
    color_mode="grayscale",
    batch_size=32,
    shuffle=False
)

test_ds = tf.keras.utils.image_dataset_from_directory(
    test_dir,
    image_size=(48, 48),
    color_mode="grayscale",
    batch_size=32,
    shuffle=False
)

normalization_layer=tf.keras.layers.Rescaling(1./255)

train_ds=train_ds.map(lambda x,y: (normalization_layer(x),y))

val_ds=val_ds.map(lambda x,y: (normalization_layer(x),y))

test_ds=test_ds.map(lambda x,y: (normalization_layer(x),y))


model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)



model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=5
)