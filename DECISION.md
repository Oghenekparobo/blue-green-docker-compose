### 1. **I trusted the image like a baby trusts milk**

The task said **“pre-built images”** – so I **believed** `yimikaade/wonderful:devops-stage-two` already had:

- `/version`
- `/chaos/start`
- `/healthz`

**Blue = Green = same image**  
I just changed `APP_POOL=blue` or `green` and `RELEASE_ID`.

**I didn’t build anything — I just used it.**

---

### 2. **Nginx is the traffic boss**

I made Nginx point to **one pool at a time** using `${ACTIVE_POOL}`.

- `blue_pool` = main
- `green_pool` = backup (with `backup` flag)

If Blue fails → Nginx retries to Green → client still gets **200 OK**.  
**Zero failed requests = happy user.**

---

### 3. **I used `.env` on my Mac to test**

At first, I was **confused**:

> “Do I need to write a Node.js app?”  
> “Do I run `npm start`?”

Then I realized:

> **The image IS the Node.js app.**  
> I don’t need to code — I just **orchestrate**.

So I made a real `.env` file locally:

```env
BLUE_IMAGE=
ACTIVE_POOL=
```
