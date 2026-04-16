# Report - Homework 3b

This was a fun homework assignment to do. At the beginning, I pretty much used the code from the lectures. It was a really good structure as in how to have a team of agents given a YAML file. 

For this I had two agents. A main agent, and a guardrail_message agent, which I passed to the main agent as a tool. I kept the prompt of avoiding messages about felines. When I tried the chat, I received that I had already mentioned the forbiden word — I had not even talked to the chat yet. Which was interesting, but also frustrating. Another thing that I noticed is that I had had to physically tell the agent that it had to physically use the conclude tool and the chat was struggling in ending the conversation otherwise. 

I then edited the prompt a little bit to see if I was able to get it to work better. That and change the guardraling topic of censorship. 

I then changed the topic to sodas and anything soda related. The agents did a great job in avoiding the forbidin topic, specially the guardrail. However I still encountered the issue with concluding after a certain number of violations happened. Now I was able to get it to terminate once I entered an emtpy message, which I was not able to do before. 

Now, here is where I realized how expensive other models are. In this conversation, I sepnt a wopping 3 cents. Most of that, 2/3 of it actually, came from the gpt-5-mini model. I was curious to what would happen if I were to change the models, so that is what I did. 

I then repeated the chat. Exact same user input. It looks like nano seems a better fit for chat related topics while gpt-5-mini is a better fit for guardrailing. It also was cheaper. In this case, it was 2 cents with nano in this case being the more expensive model. In this case, nano, did ended the chat when repeated violations, which I was placently surprised. 

Overall I found this homework really interesting. I can totally see the power of this. I can see intricate architecture that can be done. I was also surprised by the performance difference among models. Sometimes a more expensive model might not be appropriate for certain tasks. 