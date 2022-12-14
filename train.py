import argparse

import pytorch_lightning as pl
import torch
from pytorch_lightning.loggers import WandbLogger
from torch.nn import functional as F

import constants
from lightling_wrapper import BaseTorchLightlingWrapper, SpeechCommandDataModule
from models.bc_resnet.bc_resnet_model import BcResNetModel
from models.bc_resnet.mel_spec_dataset import MelSpecDataSet, mel_collate_fn
from models.simple_conv.base_dataset import AudioArrayDataSet, simconv_collate_fn
from models.simple_conv.simple_conv_model import SimpleConv


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str)
    parser.add_argument("--batch_size", type=int, default=constants.BATCH_SIZE)
    parser.add_argument("--lr", type=float, default=constants.LEARNING_RATE)
    parser.add_argument("--epochs", type=int, default=constants.EPOCHS)

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.model == "conv" or args.model is None:
        core_model = SimpleConv(n_channel=constants.N_CHANNEL, kernel_size_l1=constants.KERNEL_SIZE_L1)
        loss_fn = F.nll_loss
        collate_fn = simconv_collate_fn
        dataset_fn = AudioArrayDataSet
    elif args.model == "bc_resnet":
        core_model = BcResNetModel(
            scale=constants.SCALE_BC_RESNET, dropout=constants.DROPOUT)
        loss_fn = F.nll_loss
        collate_fn = mel_collate_fn
        dataset_fn = MelSpecDataSet
    else:
        raise ValueError("Invalid model name")

    pl.seed_everything(0)
    wandb_logger = WandbLogger(project="ViT_experiments")
    model = BaseTorchLightlingWrapper(
        core_model=core_model,
        loss_fn=loss_fn,
        learning_rate=args.lr,
    )

    data_module = SpeechCommandDataModule(
        dataset_fn, collate_fn, batch_size=args.batch_size
    )

    if torch.cuda.is_available():
        trainer = pl.Trainer(
            accelerator="gpu", devices=1, max_epochs=args.epochs, logger=wandb_logger
        )
    else:
        trainer = pl.Trainer(max_epochs=args.epochs, logger=wandb_logger)

    trainer.fit(model, data_module)
    trainer.test(model, data_module, ckpt_path="best")
