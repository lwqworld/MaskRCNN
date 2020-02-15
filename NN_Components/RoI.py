from Debugger import DebugPrint
import numpy as np
import tensorflow as tf
from NN_Components import Backbone


class RoI:
    def __init__(self, backbone_model, IMG_SHAPE, n_output_classes=80,lr=1e-4):
        self.backbone_model = backbone_model
        self.lr = lr
        self.input_bockbone = tf.keras.Input(shape=backbone_model.input.shape[1:], dtype=tf.float32,
                                             name='BACKBONE_INPUT')
        proposal_boxes = tf.keras.Input(shape=(4,), batch_size=None, name='PROPOSAL_BOXES', dtype=tf.float32)
        feature_map_shape = self.backbone_model.layers[-1].output_shape[1:]
        feature_map = tf.keras.Input(shape=feature_map_shape, batch_size=None, name='FEATURE_MAP', dtype=tf.float32)

        shape1 = tf.shape(proposal_boxes, out_type=tf.int32)
        n_boxes = tf.gather_nd(shape1, [0])
        indices = tf.zeros(shape=n_boxes, dtype=tf.int32)  # only input 1 image, all indices are 0
        img_shape_constant = tf.constant([IMG_SHAPE[0], IMG_SHAPE[1], IMG_SHAPE[0], IMG_SHAPE[1]], tf.float32)
        proposal_boxes2 = tf.math.divide(proposal_boxes, img_shape_constant)

        image_crop = tf.image.crop_and_resize(feature_map, proposal_boxes2, indices, [7, 7])
        flatten1 = tf.keras.layers.GlobalAveragePooling2D()(image_crop)
        fc1 = tf.keras.layers.Dense(units=1024, activation='relu')(flatten1)
        class_header = tf.keras.layers.Dense(units=n_output_classes+1, activation='softmax')(fc1)
        box_reg_header = tf.keras.layers.Dense(units=4, activation='linear')(fc1)

        self.RoI_header_model = tf.keras.Model(inputs=[feature_map, proposal_boxes],
                                               outputs=[class_header, box_reg_header],
                                               name='RoI_HEADER_MODEL')
        backbone_out = self.backbone_model(self.input_bockbone)
        RoI_with_backbone_out1, RoI_with_backbone_out2 = self.RoI_header_model([backbone_out, proposal_boxes])
        self.RoI_with_backbone_model = tf.keras.Model(inputs=[self.input_bockbone, proposal_boxes],
                                                      outputs=[RoI_with_backbone_out1, RoI_with_backbone_out2])

        # --- for train step ---
        self.huber = tf.keras.losses.Huber()
        self.optimizer_with_backbone = tf.keras.optimizers.Adam(self.lr)
        self.optimizer_header = tf.keras.optimizers.Adam(self.lr)

    def visualize_model(self):
        tf.keras.utils.plot_model(self.RoI_header_model, 'RoI_header_model.png', show_shapes=True)
        tf.keras.utils.plot_model(self.RoI_with_backbone_model, 'RoI_with_backbone_model.png', show_shapes=True)

    @tf.function
    def train_step_with_backbone(self, input_image, proposal_box, class_header, box_reg_header):
        with tf.GradientTape() as RoI_tape:
            class_pred, box_reg_pred = self.RoI_with_backbone_model([input_image, proposal_box])
            class_loss = tf.keras.losses.sparse_categorical_crossentropy(y_true=class_header, y_pred=class_pred)

            box_reg_loss = self.huber(y_true=box_reg_header, y_pred=box_reg_pred)
            total_loss = tf.reduce_mean(tf.add(class_loss, box_reg_loss))
        gradients = RoI_tape.gradient(total_loss, self.RoI_with_backbone_model.trainable_variables)
        self.optimizer_with_backbone.apply_gradients(zip(gradients, self.RoI_with_backbone_model.trainable_variables))

    @tf.function
    def train_step_header(self, input_image, proposal_box, class_header, box_reg_header):
        with tf.GradientTape() as RoI_tape:
            class_pred, box_reg_pred = self.RoI_with_backbone_model([input_image, proposal_box])
            class_loss = tf.keras.losses.sparse_categorical_crossentropy(y_true=class_header, y_pred=class_pred)

            box_reg_loss = self.huber(y_true=box_reg_header, y_pred=box_reg_pred)
            total_loss = tf.reduce_mean(tf.add(class_loss, box_reg_loss))
        gradients = RoI_tape.gradient(total_loss, self.RoI_header_model.trainable_variables)
        self.optimizer_header.apply_gradients(zip(gradients, self.RoI_header_model.trainable_variables))


if __name__ == '__main__':
    b1 = Backbone()
    t1 = RoI(b1.backbone_model, IMG_SHAPE=(800, 1333, 3))
    t1.visualize_model()