import json
import numpy as np
import cv2 as cv
import matplotlib.pyplot as plt
from Data_Helper import coco_tools
import random
from NN_Helper import bbox_tools, gen_candidate_anchors
import tensorflow as tf
from tensorflow.keras.utils import Sequence


class NN_data_generator():
    def __init__(self, file, imagefolder_path,
                 base_size,
                 ratios,
                 scales,
                 n_anchors,
                 img_shape_resize=(720, 1280), img_shape_ori=(720, 1280), n_stage=5,
                 threshold_iou_rpn = 0.7,
                 threshold_iou_roi = 0.55
                 ):
        # TODO: complete the resize part of the data generator
        self.threshold_iou_rpn = threshold_iou_rpn
        self.threshold_iou_roi = threshold_iou_roi
        self.dataset_coco = coco_tools(file, imagefolder_path)
        self.anchor_generator = gen_candidate_anchors(base_size=base_size,ratios=ratios, scales=scales, img_shape=img_shape_resize, n_stage=n_stage, n_anchors=n_anchors)
        self.img_shape_ori = img_shape_ori
        self.img_shape_resize = img_shape_resize

    def _resize_img(self, img):
        return cv.resize(img, self.img_shape_resize, cv.INTER_LINEAR)

    def _resize_box(self, box):
        pass

    def gen_train_input_one(self, image_id):
        return self.dataset_coco.GetOriginalImage(image_id=image_id)

    def gen_train_target_anchor_boxreg_for_RPN(self, image_id, debuginfo=False):
        bboxes = self.dataset_coco.GetOriginalBboxesList(image_id=image_id)

        # === resize ===

        bboxes_ious = []  # for each gt_bbox calculate ious with candidates
        for bbox in bboxes:
            ious = bbox_tools.ious(self.anchor_generator.anchor_candidates_list, bbox)
            ious_temp = np.ones(shape=(len(ious)), dtype=np.float) * 0.5
            # other author's implementations are use -1 to indicate ignoring, here use 0.5 to use max
            ious_temp = np.where(np.asarray(ious) > self.threshold_iou_rpn, 1, ious_temp)
            ious_temp = np.where(np.asarray(ious) < 0.3, 0, ious_temp)
            ious_temp[np.argmax(ious)] = 1
            bboxes_ious.append(ious_temp)

        # for each candidate anchor, determine the anchor target
        anchors_target = np.array(bboxes_ious)
        anchors_target = np.max(anchors_target, axis=0)
        anchors_target = np.reshape(anchors_target, newshape=(
            self.anchor_generator.h, self.anchor_generator.w, self.anchor_generator.n_anchors))
        if debuginfo:
            print(f"[Debug INFO] Number of total gt bboxes :{len(bboxes)}")
            print(
                f"[Debug INFO] Number of total target anchors: {anchors_target[np.where(anchors_target == 1)].shape[0]}")
            print(f"[Debug INFO] Shape of anchors_target: {anchors_target.shape}")
            print(
                f"[Debug INFO] Selected anchors: \n {self.anchor_generator.anchor_candidates[np.where(anchors_target == 1)]}")
        # test
        # self.anchor_generator.anchors_candidate[np.where(anchors_target==1)] = self.anchor_generator.anchors_candidate[np.where(anchors_target==1)] +100
        # print(f"Selected anchors: \n {self.anchor_generator.anchors_candidate[np.where(anchors_target == 1)]}")

        # for each gt_box, determine the box reg target
        bbox_reg_target = np.zeros(
            shape=(self.anchor_generator.h, self.anchor_generator.w, self.anchor_generator.n_anchors, 4),
            dtype=np.float)
        for index, bbox_ious in enumerate(bboxes_ious):
            ious_temp = np.reshape(bbox_ious, newshape=(
                self.anchor_generator.h, self.anchor_generator.w, self.anchor_generator.n_anchors))
            gt_box = bboxes[index]
            candidate_boxes = self.anchor_generator.anchor_candidates[np.where(ious_temp == 1)]
            # print(candidate_boxes,gt_box)
            box_reg = bbox_tools.bbox_regression_target(candidate_boxes, gt_box)
            # print(box_reg)
            # print(bbox_tools.bbox_reg2truebox(candidate_boxes, box_reg))
            bbox_reg_target[np.where(ious_temp == 1)] = box_reg

        # !!!!!!!!!!!!!!This part is for simulate the loss function with numpy and tensorflow. Don't Delate!!!!!!!!!!!!!!!
        # determine the weight, this will be implement in the tensorflow loss function in the future
        # bbox_inside_weight = np.ones(shape=(self.anchor_generator.h, self.anchor_generator.w, self.anchor_generator.n_anchors), dtype=np.float) * -1
        # print(f"[Debug INFO NP REF] Original weight in target loc: {bbox_inside_weight[np.where(anchors_target==1)]}")
        # bbox_inside_weight[np.where(anchors_target==1)] = bbox_inside_weight[np.where(anchors_target==1)] * 0 + 1
        # print(f"[Debug INFO NP REF] Modified weight in target loc: {bbox_inside_weight[np.where(anchors_target == 1)]}")
        # print(f"[Debug INFO NP REF] Number of foreground : {bbox_inside_weight[np.where(bbox_inside_weight == 1)].shape[0]}")
        # n_zeros = bbox_inside_weight[np.where(anchors_target==0)].shape[0]
        # temp_random_choice = [-1] * (n_zeros-128) + [1] * 128
        # random.shuffle(temp_random_choice)
        # # print(np.array(temp_random_choice))
        # bbox_inside_weight[np.where(anchors_target == 0)] = np.array(temp_random_choice)
        # print(f"[Debug INFO NP REF] Number of foreground + 128 random chose background : {bbox_inside_weight[np.where(bbox_inside_weight == 1)].shape[0]}")
        # bbox_outside_weight = None
        #
        # # test tensorflow
        # bbox_inside_weight = tf.ones(
        #     shape=(self.anchor_generator.h, self.anchor_generator.w, self.anchor_generator.n_anchors)) * -1
        # indices_foreground = tf.where(tf.equal(anchors_target, 1))
        # n_foreground = indices_foreground.get_shape().as_list()[0]
        # print(f"[Debug INFO TF TEST] Original weight in target loc: {tf.gather_nd(params=bbox_inside_weight, indices=indices_foreground)}")
        # bbox_inside_weight = tf.tensor_scatter_nd_update(tensor=bbox_inside_weight, indices=indices_foreground, updates=[1]*len(indices_foreground))
        # print(f"[Debug INFO TF TEST] Modified weight in target loc: {tf.gather_nd(params=bbox_inside_weight, indices=indices_foreground)}")
        # print(f"[Debug INFO TF TEST] Number of foreground : {len(indices_foreground)}")
        # indices_background = tf.where(tf.equal(anchors_target, 0))
        # print(indices_background.get_shape().as_list())
        # n_background = indices_background.get_shape().as_list()[0]
        # print(n_background)
        # selected_ratio = n_foreground/n_background
        # remain_ration = (n_background-n_foreground)/n_background
        # print(selected_ratio, remain_ration)
        # # temp_random_choice = tf.random.categorical(tf.math.log([[remain_ration, selected_ratio]]), n_background)
        # # temp_random_choice = tf.reshape(temp_random_choice, (-1,))
        # # temp_random_choice = tf.dtypes.cast(temp_random_choice, tf.float32)
        #
        # temp_random_choice = tf.random.categorical(tf.math.log([[remain_ration, selected_ratio]]), 23*40*9)
        # temp_random_choice = tf.reshape(temp_random_choice, (23,40,9))
        # temp_random_choice = tf.gather_nd(temp_random_choice, indices_background)
        # temp_random_choice = tf.dtypes.cast(temp_random_choice, tf.float32)
        # # print(np.array(temp_random_choice))
        # bbox_inside_weight = tf.tensor_scatter_nd_update(tensor=bbox_inside_weight, indices=indices_background, updates=temp_random_choice)
        # indices_train = tf.where(tf.equal(bbox_inside_weight, 1))
        #
        # print(
        #     f"[Debug INFO TF TEST] Number of foreground + {n_foreground} random chose background : {len(indices_train)}")

        return anchors_target, bbox_reg_target

    def gen_target_anchor_bboxes_classes_for_Debug(self, image_id, debuginfo=False):
        bboxes = self.dataset_coco.GetOriginalBboxesList(image_id=image_id)
        SparseTargets = self.dataset_coco.GetOriginalCategorySparseList(image_id=image_id)

        bboxes_ious = []  # for each gt_bbox calculate ious with candidates
        for bbox in bboxes:
            ious = bbox_tools.ious(self.anchor_generator.anchor_candidates_list, bbox)
            ious_temp = np.ones(shape=(len(ious)), dtype=np.float) * 0.5
            # other author's implementations are use -1 to indicate ignoring, here use 0.5 to use max
            ious_temp = np.where(np.asarray(ious) > self.threshold_iou_rpn, 1, ious_temp)
            ious_temp = np.where(np.asarray(ious) < 0.3, 0, ious_temp)
            ious_temp[np.argmax(ious)] = 1
            bboxes_ious.append(ious_temp)

        # for each gt_box, determine the box reg target
        target_anchor_bboxes = []
        target_classes = []
        for index, bbox_ious in enumerate(bboxes_ious):
            ious_temp = np.reshape(bbox_ious, newshape=(
                self.anchor_generator.h, self.anchor_generator.w, self.anchor_generator.n_anchors))
            candidate_boxes = self.anchor_generator.anchor_candidates[np.where(ious_temp == 1)]
            n = candidate_boxes.shape[0]
            for i in range(n):
                target_anchor_bboxes.append(candidate_boxes[i])
                target_classes.append(SparseTargets[index])
        return target_anchor_bboxes, target_classes

    def gen_train_data_RPN_one(self, image_id):
        input1 = self.gen_train_input_one(image_id)
        anchor_target, bbox_reg_target = self.gen_train_target_anchor_boxreg_for_RPN(image_id)
        return np.array([input1]).astype(np.float), np.array([anchor_target]).astype(np.float), np.array(
            [bbox_reg_target]).astype(np.float)

    def gen_train_data_RPN_all(self):
        inputs = []
        anchor_targets = []
        bbox_reg_targets = []
        for image_id in self.dataset_coco.image_ids:
            inputs.append(self.gen_train_input_one(image_id))
            anchor_target, bbox_reg_target = self.gen_train_target_anchor_boxreg_for_RPN(image_id)
            anchor_targets.append(anchor_target)
            bbox_reg_targets.append(bbox_reg_target)
        return np.array(inputs).astype(np.float), np.array(anchor_targets), np.array(bbox_reg_targets)

    def gen_train_data_RoI_one(self, image_id, bbox_list):
        gt_bboxes = self.dataset_coco.GetOriginalBboxesList(image_id=image_id)
        SparseTargets = self.dataset_coco.GetOriginalCategorySparseList(image_id=image_id)

        bboxes_ious = []  # for each gt_bbox calculate ious with candidates
        for bbox in gt_bboxes:
            ious = bbox_tools.ious(bbox_list, bbox)
            ious_temp = np.zeros(shape=(len(ious)), dtype=np.float)
            # other author's implementations are use -1 to indicate ignoring, here use 0.5 to use max
            ious_temp = np.where(np.asarray(ious) > self.threshold_iou_roi, 1, ious_temp)
            ious_temp[np.argmax(ious)] = 1
            bboxes_ious.append(ious_temp)

        # for each gt_box, determine the box reg target
        original_img = self.gen_train_input_one(image_id)
        input_images = []
        input_box_filtered_by_iou = []
        target_classes = []
        target_bbox_reg = []
        for index_gt, bbox_ious in enumerate(bboxes_ious):
            candidate_boxes = np.asarray(bbox_list)[np.where(bbox_ious == 1)]
            n = candidate_boxes.shape[0]
            for i in range(n):
                input_box_filtered_by_iou.append(candidate_boxes[i].astype(np.float))
                box_reg = bbox_tools.bbox_regression_target(pred_boxes=candidate_boxes[i].reshape((1, 4)),
                                                            gt_box=gt_bboxes[index_gt])
                target_bbox_reg.append(box_reg.ravel())
                target_classes.append(SparseTargets[index_gt])
                input_images.append(original_img.astype(np.float))
        for index_gt, bbox_gt in enumerate(gt_bboxes):
            input_images.append(original_img.astype(np.float))
            input_box_filtered_by_iou.append(bbox_gt.astype(np.float))
            target_classes.append(SparseTargets[index_gt])
            target_bbox_reg.append(np.array([0, 0, 0, 0], dtype=np.float))
        return np.asarray(input_images).astype(
            np.float), np.asarray(input_box_filtered_by_iou), np.asarray(target_classes), np.asarray(
            target_bbox_reg)

    def _validate_bbox(self, image_id, bboxes):
        img1 = self.dataset_coco.GetOriginalImage(image_id=image_id)
        for bbox in bboxes:
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            img1 = cv.rectangle(img1, (bbox[1], bbox[0]), (bbox[3], bbox[2]), color, 4)
        plt.imshow(img1)
        plt.show()

    def _validata_masks(self, image_id):
        img1 = self.dataset_coco.GetOriginalImage(image_id=image_id)
        temp_img = np.zeros(shape=img1.shape, dtype=np.uint8)
        Masks = self.dataset_coco.GetOriginalSegmsMaskList(image_id=image_id)
        for mask in Masks:
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            temp_img[:, :, 0][mask.astype(bool)] = color[0]
            temp_img[:, :, 1][mask.astype(bool)] = color[1]
            temp_img[:, :, 2][mask.astype(bool)] = color[2]
        img1 = (img1 * 0.5 + temp_img * 0.5).astype(np.uint8)
        plt.imshow(img1, cmap='gray')
        plt.show()


def test2():
    BASE_PATH = '/Users/shuzhiliu/Google Drive/KyoceraRobotAI/mmdetection_tools/data'
    imagefolder_path = '/Users/shuzhiliu/Google Drive/KyoceraRobotAI/mmdetection_tools/LocalData_Images'
    DATASET_ID = '1940091026744'
    image_id = '20191119T063709-cca043ed-32fe-4da0-ba75-e4a12b88eef4'
    t1 = NN_data_generator(file=f"{BASE_PATH}/{DATASET_ID}/annotations/train.json",
                           imagefolder_path=imagefolder_path)
    bboxes = t1.dataset_coco.GetOriginalBboxesList(image_id=image_id)
    t1._validate_bbox(image_id=image_id, bboxes=bboxes)
    t1._validata_masks(image_id=image_id)
    t1.gen_train_target_anchor_boxreg_for_RPN(image_id=image_id)


def test():
    BASE_PATH = '/Users/shuzhiliu/Google Drive/KyoceraRobotAI/mmdetection_tools/data'
    imagefolder_path = '/Users/shuzhiliu/Google Drive/KyoceraRobotAI/mmdetection_tools/LocalData_Images'
    DATASET_ID = '1940091026744'
    image_id = '20191119T063709-cca043ed-32fe-4da0-ba75-e4a12b88eef4'
    data1 = coco_tools(jsonfile=f"{BASE_PATH}/{DATASET_ID}/annotations/train.json",
                       imagefolder_path=imagefolder_path)
    img1 = data1.GetOriginalImage(image_id=image_id)
    print(data1.images)
    bboxes = data1.GetOriginalBboxesList(image_id=image_id)
    print(bboxes)
    # img1 = np.zeros(shape=(720,1280,3), dtype=np.uint8)
    for bbox in bboxes:
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        # cv.rectangle(img1,(bbox[0],bbox[1]), (bbox[2],bbox[3]), 255)
        # print(bbox)
        # cv.rectangle(img=img1,rec=(bbox[1],bbox[0],bbox[3]-bbox[1],bbox[2]-bbox[0]), color=color, thickness=4)
        cv.rectangle(img1, (bbox[1], bbox[0]), (bbox[3], bbox[2]), color, 4)
    plt.imshow(img1)
    plt.show()

    g1 = gen_candidate_anchors()
    print(len(g1.anchor_candidates_list))
    ious = bbox_tools.ious(g1.anchor_candidates_list, bboxes[0])
    ious[np.argmax(ious)] = 1
    print(len(ious))
    ious_np = np.reshape(ious, newshape=(23, 40, 9))
    index = np.where(ious_np == 1)
    print(index)
