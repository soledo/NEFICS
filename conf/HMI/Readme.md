# HMI configurations

For the HMI devices, we use [FUXA](https://github.com/frangoteam/FUXA) as the provider of all the HMI functionalities. This HMI folder contains different HMI configurations exported from FUXA.

For the first run of any scenario, follow the instructions provided by FUXA to install and run the HMI server in the appropriate simulated HMI device.

In summary, after you download and unpack the latest release, run:

```
cd ./server
npm install
npm start
```

This will start the web HMI in port 1881 of the simulated HMI. You can access this via a web browser and load any of the configurations provided in this folder, which have already been adjusted to match the different scenarios.

The currently available scenarios are:

| NEFICS | FUXA |
| ----------- | ----------- |
| honeypot_warehouse.json | Warehouse.json |
| honeypot_watertank.json | Watertank.json |

