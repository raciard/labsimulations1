
# **Car Sharing Simulation — Lab Report**

## **Main Objective of the Lab**

The main objective of this lab is to develop and analyze a simulation model that represents the functioning of a car-sharing system in an urban environment.

In this system:

* Users appear randomly at various locations and use a smartphone application to locate and reserve a nearby available car.
* Once a reservation is made, users drive the car to their chosen destination and leave it either at designated charging stations or in any available public parking space.
* Vehicles with low battery levels are identified for relocation, and dedicated agents (relocators) move these vehicles to charging stations to ensure the fleet remains operational and balanced across the service area.

The simulation aims to understand how key parameters—such as fleet size, number of charging stations, user arrival rate, and relocator capacity—affect the overall system performance. By analyzing these dynamics, the lab explores the relationships between demand, resource availability, and system efficiency in shared mobility networks.

---

## **1) Key Parameters and Performance Indicators**

### **Key Parameters**

The system is characterized by several configurable parameters that determine how it behaves over time:

* **Fleet size:** the total number of vehicles available for users.
* **Number of charging stations:** the amount of infrastructure available for electric vehicle recharging.
* **Number of relocators:** the number of workers or agents responsible for moving cars to charging stations or high-demand areas.
* **User arrival rate:** how frequently new users enter the system to request a car.
* **Trip duration and distance:** the average time and distance users travel between pickup and drop-off.
* **Charging characteristics:** include station capacity, charging speed, and the minimum battery threshold that triggers recharging.
* **Relocation speed and policy:** determine how quickly and efficiently cars are moved when required.
* **Spatial layout:** includes the simulated map size and the distribution of trip origins and destinations.

### **Performance Indicators (KPIs)**

To evaluate the system’s performance, the following indicators are analyzed:

* **Availability rate:** proportion of users who find a car available immediately.
* **Reservation success rate:** fraction of users who eventually obtain a car after possible retries.
* **Average waiting time:** time between a user’s reservation and the start of their trip.
* **Vehicle utilization rate:** percentage of time cars are actively used compared to being idle or charging.
* **Charging station utilization:** proportion of time charging points are occupied.
* **Relocation activity:** number of relocation tasks performed per unit of time.
* **System throughput:** total number of completed trips during the simulation.

---

## **2) Model Design**

### **Modeling Approach**

The simulation models the real-world operation of a car-sharing system using discrete events. Each event represents an action in time—such as a user arriving, picking up a car, completing a trip, or a car starting to charge.

The key entities in the model are:

* **Users:** appear randomly, request vehicles, and perform trips.
* **Cars:** move between available, in-use, charging, or relocating states.
* **Charging stations:** manage queues of vehicles waiting or currently charging.
* **Relocators:** transport low-battery cars to available charging points.

### **Balance Between Accuracy and Simplicity**

The model prioritizes capturing realistic operational behavior without introducing unnecessary complexity. It includes essential processes such as user arrivals, trip generation, battery depletion, and charging dynamics.

However, it simplifies aspects like detailed traffic conditions, lane-level interactions, and second-by-second vehicle movements. Instead, trip times and distances are represented through estimated averages, ensuring the simulation remains efficient and focused on system-level performance.

### **User Mobility Model**

Users are assumed to appear at random locations across the service area. Trip origins and destinations are sampled independently, typically following a uniform distribution. The user always selects the nearest available vehicle, and walking time to reach it is estimated based on average walking speed and distance.

This setup allows the model to approximate realistic spatial movement patterns while maintaining mathematical simplicity.

### **Stationarity of Mobility Patterns**

The current simulation assumes **stationary mobility patterns**—that is, the rate at which users appear and the spatial distribution of trips remain constant throughout the simulated period. This assumption simplifies analysis and is suitable for evaluating average system behavior.

If needed, the model could later be extended to include **time-dependent variations**, such as rush-hour peaks or regional demand differences.

---

## **3) Data Structures**

The simulation relies on structured representations of entities and events to track system evolution over time.

The most important data structure is the **Future Event Set (FES)**—a queue that stores all scheduled events in chronological order. The simulation processes events one by one based on their scheduled times, updating the system state as each event occurs.

Other supporting structures include collections for managing the lists of users, vehicles, charging stations, and relocators, as well as a simplified representation of the road network for estimating distances and travel times.

---

## **4) Assumptions**

To keep the model manageable and focused on system-level behavior, the following assumptions are made:

1. **User arrivals** follow a Poisson process, meaning inter-arrival times are exponentially distributed.
2. **Trip origins and destinations** are chosen independently and uniformly across the map.
3. **Users always choose the nearest available car** and walk to it at an average speed.
4. **Energy consumption** during trips is directly proportional to travel distance.
5. **Charging stations** have limited capacity and operate on a first-come, first-served basis.
6. **Relocators** are limited in number and only move cars when their battery levels fall below a threshold.
7. **All events occur instantaneously** at their scheduled times, without intermediate updates.
8. **User behavior** is consistent throughout the simulation (no learning or adaptive decision-making).
9. **Spatial and temporal stationarity** is assumed for simplicity—demand and traffic conditions do not vary with time.

---

## **Conclusion**

This simulation provides a controlled environment to study the complex interactions within a car-sharing system. By adjusting parameters such as fleet size, number of stations, and relocation policies, it becomes possible to evaluate system performance under different configurations.

The analysis of key indicators—like availability, waiting time, and utilization—helps identify operational trade-offs and design choices that improve service efficiency and sustainability in shared urban mobility systems.

