# Lithium-Flower

Prompt tuning framework. Playing with [Lithium-Flower](https://www.youtube.com/watch?v=Wolcpa9s6NU)

- **About Lithium-Flower**

> lithium flower · Scott Matthew · 菅野よう子 · ティム・ジャンセン/TIM JENSEN
> 
> GHOST IN THE SHELL: STAND ALONE COMPLEX O.S.T.+

## Reference
- [agent-lightning](https://github.com/microsoft/agent-lightning)
- [DSPy](https://github.com/stanfordnlp/dspy)

## **agent lightning store**

```sh
cd docker
docker build -t agl/store:dev -f Dockerfile .
docker compose up -d
docker compose down
rm -r ./data
```
- store dashboard: `http://localhost:45993`
