# Lithium-Flower

Prompt tuning framework. Playing with [Lithium-Flower](https://www.youtube.com/watch?v=Wolcpa9s6NU)

- **About Lithium-Flower**

> lithium flower · Scott Matthew · 菅野よう子 · ティム・ジャンセン/TIM JENSEN
> 
> GHOST IN THE SHELL: STAND ALONE COMPLEX O.S.T.+

## Reference
- [agent-lightning](https://github.com/microsoft/agent-lightning)
- [DSPy]()

## agent lightning store

```sh
docker build -t agl/store:dev -f Dockerfile .
docker rm -f agl-store
docker run -d --user root -p 45993:4747 --name agl-store agl/store:dev agl store --host 0.0.0.0 --port 4747 --log-level DEBUG

docker compose up -d
mongosh --eval "db.adminCommand('ping')"
docker compose down
rm -r ./data
```

### client
```sh
docker run -d --network host \
-v .//src://app//src \
--name agl-cli agl/store:dev sleep infinity

docker rm -f agl-cli

```

```sh
source /home/siao/.venv/bin/activate


```
