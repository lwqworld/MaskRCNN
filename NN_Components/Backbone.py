import tensorflow as tf
import inspect


def backbone_test():
    img_shape = (224, 224, 3)
    input1 = tf.keras.Input(shape=img_shape)
    base_model = tf.keras.applications.ResNet50V2(input_shape=img_shape,
                                                  include_top=True)
    # entire pretrained model
    tf.keras.utils.plot_model(model=base_model, to_file='test_base_model.png', show_shapes=True)
    # two methods to build test base_model2
    # base_model2 = tf.keras.Model(inputs=[base_model.layers[0].output], outputs=[base_model.layers[-3].output])
    base_model2 = tf.keras.Model(inputs=[base_model.get_layer(index=0).input],
                                 outputs=[base_model.get_layer(index=-3).output])
    tf.keras.utils.plot_model(model=base_model2, to_file='test_base_model_cut.png', show_shapes=True)
    # To build base_model3, we need input layer
    input2 = tf.keras.Input(shape=(7, 7, 2048))
    base_model3 = tf.keras.Model(inputs=[input2], outputs=[base_model.get_layer(index=-2)(input2)])
    tf.keras.utils.plot_model(model=base_model3, to_file='test_base_model_cut2.png', show_shapes=True)
    # better use Sequential API
    base_model4 = tf.keras.Sequential(layers=[
        input2,
        base_model.get_layer(index=-2),
        base_model.get_layer(index=-1)
    ])
    # Check if the weights are same in two models
    print(base_model.layers[-1].get_weights()[0].flatten()[:5])
    print(base_model4.layers[-1].get_weights()[0].flatten()[:5])
    tf.keras.utils.plot_model(model=base_model4, to_file='test_base_model_cut3.png', show_shapes=True)
    # print(base_model.summary())
    conv1 = tf.keras.layers.Conv2D(filters=256, kernel_size=(1, 1), padding='same')
    bh1 = tf.keras.layers.BatchNormalization()
    ac1 = tf.keras.layers.Activation(activation=tf.keras.activations.relu)
    model2 = tf.keras.Model(inputs=[input1], outputs=[ac1(bh1(conv1(base_model2(input1))))])  # try functional API
    # Try Sequential API, better use Sequential API
    # model2 = tf.keras.Sequential(layers=[
    #     input1,
    #     base_model,
    #     conv1,
    #     bh1,
    #     ac1
    # ])
    tf.keras.utils.plot_model(model=model2, to_file='test_base_model_modified.png', show_shapes=True)

    print(len(base_model.layers))


class Backbone:
    def __init__(self, img_shape=(800, 1333, 3), n_stage=5):
        # the stages of other implementation is 4, note that this ResNet50V2 has 5!
        self.base_model = tf.keras.applications.ResNet50V2(input_shape=img_shape,
                                                           include_top=False)
        if n_stage == 4:
            self.backbone_model = tf.keras.Model(inputs=[self.base_model.input], outputs=[
                self.base_model.get_layer(name='conv4_block6_preact_relu').output], name='BACKBONE_MODEL')
        elif n_stage == 5:
            self.backbone_model = tf.keras.Model(inputs=[self.base_model.input], outputs=[self.base_model.output],
                                                 name='BACKBONE_MODEL')

    def visualize_model(self):
        tf.keras.utils.plot_model(model=self.backbone_model, to_file='base_model_modified.png', show_shapes=True)

    def get_output_shape(self):
        return self.backbone_model.layers[-1].output_shape[1:]  # first dim is batch size

    def save_weight(self, root_path):
        self.backbone_model.save_weights(filepath=f"{root_path}/backbone_model")

    def load_weight(self, root_path):
        self.backbone_model.load_weights(filepath=f"{root_path}/backbone_model")


if __name__ == '__main__':
    t1 = Backbone()
    t1.visualize_model()
    backbone_test()
