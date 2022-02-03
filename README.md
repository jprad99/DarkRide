# DarkRide
PLEASE NOTE: This project is not Open Source (Yet) and is at this time only public for educational purposes. Your respect of this is greatly appreciated!
# The idea
This repository is home to the first component of my Modular Attractions Platform project. The goal is to create a system that would allow for theme parks and family entertainment centers to create, or hire a company which could create, a classic-style dark ride attraction that requires minimal infrastructure, utilizes open-source software, and unlike existing "classic" dark rides features a computerized control system where props, control panels, and of course the ride vehicles are all connected over a network to a central database. The vehicles also feature variable speed, and the system is _technically_ trackless, though not in the modern sense - it simply utilizes retroreflective tape on the floor to guide the vehicles.
The prototype utilizes components off of a mobility scooter, which offers a great torque capability. For production, I'm currently looking at the RP-T3-800B from RUPU (Jinhua Ruipu Machinery Manufacturing Co., Ltd.) due to an incredible load capacity of 500kg, along with a high torque which would offer ideal performance under such loads. The drawback is that it would require a different motor controller, and the current code is based upon the Pololu SMC G2 series. While this swap wouldn't be too hard to make, I quite like Pololu's offering. Also under consideration are some motors from AGV vehicles, designed for moving these heavy loads.
# Goals
* Have a working prototype in 2022, and partner with a facility to introduce the first public version in 2023
* Cost for the vehicle chassis & electronics should be below $1000 USD before batteries - batteries will vary by installation needs
* Chassis should be made of structural steel and able to accomodate two riders, with a vehicle capacity of 800 pounds
* Smooth out tracking by moving from a 2 sensor to a 7 sensor array & onboard micronctroller processing for PID control, or a computer vision based solution
* Full support for blocking zones and ESTOP buttons - a tie-in for fire alarms should be designed for legal compliance.
* Maintenance and operations should be simple, parts readily available for swapping in minutes or hours rather than days.
# Future Ambitions
* Onboard Audio
* Utilization of Lithium Ion (super)Capacitors for power (or standard super/ultra capacitors)
  * Rapid charging capabilities allowing for lower on board energy capacity and less downtime for charging
* RTLS based motion paths
  * Omni wheels and IMUs would thus enable a full, trackless experience
  * pozyx is a strong contender here with a low cost-of-entry for experimenting
* Hydraulic (or otherwise locking) lap bar restraints
* Source electric transaxles from a factory overseas to have one, consistent drivetrain, and easily swappable componentry
* IR/Laser blaster upgrade for interactivity (this is already in development, actually)

# Why this project?
I love classic dark rides - the ones you don't necessarily get on expecting world class animatronics, cohesive storylines, or a cutting edge technology system. Don't get me wrong, I think those are fantastic in their own rights, but I still think the charm of the classic "Haunted Mansion" style dark ride has a place.
This project is my attempt to create a platform that would allow a park to upgrade their walkthrough haunted houses to a dark ride experience, or introduce a new dark ride, without the costs associated with modern ride systems - whilst emphasizing the use of modern safety capabilities, such as network connected ESTOPs and block zones, something that the older rides had very primitive variants of.

# Personal Goal
I want to bring the first public installation to the market in September 2023, when parks introduce their Halloween events. Details are yet to come, but I plan on reaching out to numerous smaller parks across the country about this, and offering to bring my commitment to this project onto their team. While I may consider open-sourcing this project in the long run, I have no firm date in mind for that.

# For parks or engineering firms
If you happen to be stumbling upon this project, and you want to reach out - my personal website https://jamesradko.com/ will have contact information that is most up to date. This software is mostly a framework, and will feature customizations for each installation. Of course it is designed so that these changes are easy to make, but it is much easier for me as the creator to call it "easy" than it would be for someone completely new to the project. Feel free to contact me for literally anything, from questions to saying hello, or even internship offers if it's my lucky day!
