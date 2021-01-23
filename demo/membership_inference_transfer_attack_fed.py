import yaml

from fed_exchange_weight_bias.Client import *
from fed_exchange_weight_bias.Server import *
from membership_inference_attack.Attacker import *

with open("hyper_parameters.yaml", mode='r', encoding="utf-8") as f:
    hyper_parameters = yaml.load(f, Loader=yaml.FullLoader)

if __name__ == "__main__":
    dataset_config = hyper_parameters["dataset"]
    input_shape = dataset_config["input_shape"]
    classes_num = dataset_config["classes_num"]

    participant_config = hyper_parameters["participant"]
    fed_epochs = participant_config["fed_epochs"]
    learning_rate = participant_config["learning_rate"]
    batch_size = participant_config["batch_size"]
    clients_num = participant_config["clients_num"]
    client_ratio_per_round = participant_config["client_ratio_per_round"]
    client_local_epochs = participant_config["local_epochs"]

    target_participant_config = hyper_parameters["target_participant"]
    target_cid = target_participant_config["target_cid"]
    target_fed_epoch = target_participant_config["target_fed_epoch"]

    attacker_participant_config = hyper_parameters["attacker_participant"]
    attacker_cid = attacker_participant_config["attacker_cid"]
    attacker_local_epochs = attacker_participant_config["local_epochs"]

    client = Clients(input_shape=input_shape,
                     classes_num=classes_num,
                     learning_rate=learning_rate,
                     clients_num=clients_num)
    server = Server()
    attacker = Attacker(cid=attacker_cid,
                        local_epochs=attacker_local_epochs)

    attacker.declare_attack("MITA", target_cid, target_fed_epoch)
    attacker.generate_attacker_data_handler(client)

    for epoch in range(fed_epochs):
        server.initialize_local_parameters_sum()
        activated_cid_list = client.choose_clients(client_ratio_per_round)

        for cid in activated_cid_list:
            client.current_cid = cid
            print("[federated learning epoch - {}, current participant - cid {}]".format((epoch + 1), cid))

            client.download_global_parameters(server.global_parameters)

            if cid == attacker_cid:
                client.train_local_model(batch_size=batch_size, local_epochs=attacker_local_epochs)
            else:
                client.train_local_model(batch_size=batch_size, local_epochs=client_local_epochs)

            current_local_parameters = client.upload_local_parameters()
            server.accumulate_local_parameters(current_local_parameters)

            if epoch == target_fed_epoch and cid == attacker_cid:
                print("train inference model on attacker - cid {} "
                      "at federated learning epoch - {}".format(attacker_cid, target_fed_epoch))
                attacker.create_membership_inference_model(client)
                attacker.train_inference_model()
            elif epoch == target_fed_epoch and cid == target_cid:
                attacker.test_inference_model(client)

        server.update_global_parameters(len(activated_cid_list))

