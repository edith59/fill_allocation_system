<!--lint disable awesome-toc-->
## Getting started

This instruction will get you through the bootstrap phase of running
sample of containerized application with Docker Compose.

### Prerequisites

- Make sure that you have Docker and Docker Compose installed
  - Windows or macOS:
    [Install Docker Desktop](https://www.docker.com/get-started)
  - Linux: [Install Docker](https://www.docker.com/get-started) and then
    [Docker Compose](https://github.com/docker/compose)

### Running an application

1. Clone the repository
```console
git clone 
```

2. Run docker-compose file

```console
docker-compose up --build
```
The root directory contains the `docker-compose.yaml` which
describes the configuration of service components. By executing following command
you will be able to run Dockerfiles for 4 containers

### Stopping an application
To stop and remove all containers of the application run (alternatively use ctrl+c):

```console
docker-compose down
```

### General overview of problem
The controller receives trade fills from the fill servers in the following format at random intervals,
there are only 10 different stocks available:
{stock ticker: &lt;string out of 10 possibilities&gt;, price: &lt;random positive price&gt;, quantity: &lt;random
quantity&gt;}
The controller receives random account splits from the AUM server at 30 second intervals.
{account1: &lt;random percentage&gt;, account2: &lt;random percentage&gt;, …, accountn: &lt;random
percentage&gt;}
The percentages should add up to 100%
The job of the controller is to keep track of positions held by each account, as new fills come in it
tries to divide the stocks (in whole stocks) so that each account has an overall position that matches
the split from the AUM server as closely as possible, i.e., each account is allocated a number of
stocks so that the overall value of the fills they have is as closely proportional to their AUM
percentage as possible. Previous trade fills cannot be rearranged after they have been allocated.
It should report the new overall positions to the position server at 10 second intervals, the position
server should then print out the new positions/values.
