
const container = document.getElementById("container");
const boxes = document.querySelectorAll(".box, .box23");

document.body.style.margin = "0";
document.body.style.fontFamily = "Arial, sans-serif";
document.body.style.display = "flex";
document.body.style.flexDirection = "column";
document.body.style.alignItems = "center";
document.body.style.justifyContent = "center";
document.body.style.minHeight = "100vh";
document.body.style.background = "pink";

container.style.display = "flex";
container.style.gap = "20px";
container.style.maxWidth = "600px";
container.style.marginTop = "20px";

const technologies = [
  { name: "MongoDB", icon: "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/mongodb/mongodb-original.svg" },
  { name: "Express", icon: "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/express/express-original.svg" },
  { name: "React", icon: "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/react/react-original.svg" },
  { name: "Node.js", icon: "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nodejs/nodejs-original.svg" },
];

boxes.forEach((box, index) => {
  box.style.padding = "20px";
  box.style.textAlign = "center";
  box.style.fontSize = "20px";
  box.style.fontWeight = "bold";
  box.style.borderRadius = "12px";
  box.style.boxShadow = "0 4px 12px rgba(0,0,0,0.1)";
  box.style.cursor = "pointer";
  box.style.transition = "all 0.3s ease";
  box.style.background = "#fff";
  box.textContent = technologies[index].name;

  const icon = document.createElement("img");
  icon.src = technologies[index].icon;
  icon.style.width = "40px";
  icon.style.height = "40px";
  icon.style.display = "none";
  box.appendChild(icon);

  box.addEventListener("mouseenter", () => {
    box.style.transform = "scale(1.05)";
    box.style.background = "#0078ff";
    box.style.color = "#fff";
    icon.style.display = "flex";
  });

  box.addEventListener("mouseleave", () => {
    box.style.transform = "scale(1)";
    box.style.background = "#fff";
    box.style.color = "#000";
    icon.style.display = "none";
  });


});

const heading = document.querySelector("p");
heading.textContent = "Welcome to the MERN Stack dom manipulation";
heading.style.fontSize = "28px";
heading.style.fontWeight = "600";
heading.style.marginBottom = "10px";
heading.style.color = "teal";
